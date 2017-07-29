# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging
import time

import pytest
from gcdt_bundler.bundler import get_zipped_file
from nose.tools import assert_equal, assert_greater_equal

from gcdt import utils
from gcdt.ramuda_core import delete_lambda_deprecated, deploy_lambda, ping
from gcdt.ramuda_wire import _add_event_source, _remove_event_source, \
    wire, wire_deprecated, unwire, unwire_deprecated, \
    _get_event_source_status, _lambda_add_time_schedule_event_source, _lambda_add_invoke_permission
from gcdt.sns import create_topic, delete_topic
from gcdt.kinesis import create_stream, describe_stream, delete_stream
from gcdt_testtools import helpers
from gcdt_testtools.helpers import create_tempfile
from gcdt_testtools.helpers_aws import create_role_helper, delete_role_helper, \
    create_lambda_helper, create_lambda_role_helper, check_preconditions, \
    settings_requirements, check_normal_mode
from gcdt_testtools.helpers_aws import temp_bucket, awsclient, \
    cleanup_roles  # fixtures!
from gcdt_testtools.helpers import cleanup_tempfiles, temp_folder  # fixtures!
from gcdt_testtools.helpers import create_tempfile
from .test_ramuda_aws import vendored_folder, temp_lambda  # fixtures!
from .test_ramuda_aws import cleanup_lambdas, cleanup_lambdas_deprecated  # fixtures!
from . import here


log = logging.getLogger(__name__)


def _get_count(awsclient, function_name, alias_name='ACTIVE', version=None):
    """Send a count request to a lambda function.

    :param awsclient:
    :param function_name:
    :param alias_name:
    :param version:
    :return: count retrieved from lambda call
    """
    client_lambda = awsclient.get_client('lambda')
    payload = '{"ramuda_action": "count"}'

    if version:
        response = client_lambda.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=payload,
            Qualifier=version
        )
    else:
        response = client_lambda.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=payload,
            Qualifier=alias_name
        )

    # print type(response['Payload'])
    results = response['Payload'].read()  # payload is a 'StreamingBody'
    return results


@pytest.mark.aws
@pytest.mark.slow
@check_preconditions
def test_wire_unwire_new_events_with_s3(
        awsclient, vendored_folder, cleanup_lambdas, cleanup_roles,
        temp_bucket):
    log.info('running test_wire_unwire_new_events_with_s3')

    # create a lambda function
    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda_s3_event/handler_counter.py',
                         lambda_handler='handler_counter.handle')
    #cleanup_lambdas.append(lambda_name)

    bucket_name = temp_bucket

    events = [
        {
            "event_source": {
                "arn": "arn:aws:s3:::" + bucket_name,
                "events": [
                    's3:ObjectCreated:*',
                ]
            }
        }
    ]

    # wire the function with the bucket
    exit_code = wire(awsclient, events, lambda_name)
    assert exit_code == 0

    # put a file into the bucket
    awsclient.get_client('s3').put_object(
        ACL='public-read',
        Body=b'this is some content',
        Bucket=bucket_name,
        Key='test_file.gz',
    )

    # validate function call
    time.sleep(20)  # sleep till the event arrived
    assert int(_get_count(awsclient, lambda_name)) == 1

    # unwire the function
    exit_code = unwire(awsclient, events, lambda_name)
    assert exit_code == 0

    # put in another file
    awsclient.get_client('s3').put_object(
        ACL='public-read',
        Body=b'this is some content',
        Bucket=bucket_name,
        Key='test_file_2.gz',
    )

    # validate function not called
    time.sleep(10)
    assert int(_get_count(awsclient, lambda_name)) == 1


@pytest.mark.aws
@pytest.mark.slow
@check_preconditions
def test_wire_unwire_new_events_with_schedule_expression(
        awsclient, vendored_folder, cleanup_lambdas, cleanup_roles,
        temp_bucket):
    log.info('running test_wire_unwire_new_events_with_schedule_expression')

    # create a lambda function
    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda_s3_event/handler_counter.py',
                         lambda_handler='handler_counter.handle')
    cleanup_lambdas.append(lambda_name)

    # schedule expressions:
    # http://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html
    bucket_name = temp_bucket
    events = [
        {
            "event_source": {
                "schedule": "rate(1 minute)"
            }
        }
    ]

    # wire the function with the bucket
    exit_code = wire(awsclient, events, lambda_name)
    assert exit_code == 0

    assert int(_get_count(awsclient, lambda_name)) == 0

    time.sleep(70)  # sleep till scheduled event
    assert int(_get_count(awsclient, lambda_name)) == 1

    # unwire the function
    exit_code = unwire(awsclient, events, lambda_name)
    assert exit_code == 0

    time.sleep(70)
    assert int(_get_count(awsclient, lambda_name)) == 1


@pytest.mark.aws
@check_preconditions
def test_event_source_lifecycle_s3(awsclient, temp_lambda, temp_bucket):
    log.info('running test_event_source_lifecycle_s3')

    lambda_name = temp_lambda[0]

    # lookup lambda arn
    lambda_client = awsclient.get_client('lambda')
    alias_name = 'ACTIVE'
    lambda_arn = lambda_client.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']

    # define event source
    bucket_arn = 'arn:aws:s3:::' + temp_bucket
    evt_source = {
        'arn': bucket_arn, 'events': ['s3:ObjectCreated:*'],
        "suffix": ".gz"
    }

    # event source lifecycle
    _add_event_source(awsclient, evt_source, lambda_arn)
    status = _get_event_source_status(awsclient, evt_source, lambda_arn)
    assert status['EventSourceArn']
    _remove_event_source(awsclient, evt_source, lambda_arn)


@pytest.mark.aws
@check_preconditions
def test_event_source_lifecycle_cloudwatch(awsclient, temp_lambda):
    log.info('running test_event_source_lifecycle_cloudwatch')

    lambda_name = temp_lambda[0]

    # lookup lambda arn
    lambda_client = awsclient.get_client('lambda')
    alias_name = 'ACTIVE'
    lambda_arn = lambda_client.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']

    # define event source
    evt_source = {
        "name": "execute_backup",
        "schedule": "rate(1 minute)"
    }

    # event source lifecycle
    _add_event_source(awsclient, evt_source, lambda_arn)
    status = _get_event_source_status(awsclient, evt_source, lambda_arn)
    assert status['EventSourceArn']
    assert status['State'] == 'ENABLED'
    _remove_event_source(awsclient, evt_source, lambda_arn)


@pytest.fixture(scope='function')  # 'function' or 'module'
def temp_sns_topic(awsclient):
    # create a bucket
    temp_string = utils.random_string()
    arn = create_topic(awsclient, temp_string)
    yield temp_string, arn
    # cleanup
    delete_topic(awsclient, arn)


@pytest.mark.aws
@check_preconditions
def test_event_source_lifecycle_sns(awsclient, temp_lambda, temp_sns_topic):
    log.info('running test_event_source_lifecycle_sns')

    lambda_name = temp_lambda[0]

    # lookup lambda arn
    lambda_client = awsclient.get_client('lambda')
    alias_name = 'ACTIVE'
    lambda_arn = lambda_client.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']

    # define event source
    evt_source = {
        #"arn":  "arn:aws:sns:::your-event-topic-arn",
        "arn": temp_sns_topic[1],
        "events": [
            "sns:Publish"
        ]
    }

    # event source lifecycle
    _add_event_source(awsclient, evt_source, lambda_arn)
    status = _get_event_source_status(awsclient, evt_source, lambda_arn)
    assert status['EventSourceArn']
    _remove_event_source(awsclient, evt_source, lambda_arn)


@pytest.fixture(scope='function')  # 'function' or 'module'
def temp_kinesis(awsclient):
    # create a bucket
    temp_string = utils.random_string()
    create_stream(awsclient, temp_string)
    arn = describe_stream(awsclient, temp_string)['StreamARN']
    yield temp_string, arn
    # cleanup
    delete_stream(awsclient, temp_string)


@pytest.mark.aws
@check_preconditions
def test_event_source_lifecycle_kinesis(awsclient, temp_lambda, temp_kinesis):
    log.info('running test_event_source_lifecycle_sns')

    lambda_name = temp_lambda[0]

    # lookup lambda arn
    lambda_client = awsclient.get_client('lambda')
    alias_name = 'ACTIVE'
    lambda_arn = lambda_client.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']

    # define event source
    evt_source = {
        #"arn":  "arn:aws:dynamodb:us-east-1:1234554:table/YourTable/stream/2016-05-11T00:00:00.000",
        "arn": temp_kinesis[1],
        "starting_position": "TRIM_HORIZON",  # Supported values: TRIM_HORIZON, LATEST
        "batch_size": 50,  # Max: 1000
        "enabled": True  # Default is false
    }

    # event source lifecycle
    _add_event_source(awsclient, evt_source, lambda_arn)
    status = _get_event_source_status(awsclient, evt_source, lambda_arn)
    assert status['EventSourceArn']
    _remove_event_source(awsclient, evt_source, lambda_arn)


# TODO
# wire
# _get_lambda_policies
# use create_lambda_helper to simplify above testcases


################################################################################
### DEPRECATED
################################################################################
# all test code below is deprectated (related to old wire implementation)
# DEPRECATED!!
@pytest.mark.aws
@check_preconditions
def test_deprecated_schedule_event_source(
        awsclient, vendored_folder, cleanup_lambdas_deprecated, cleanup_roles):
    log.info('running test_schedule_event_source')
    # include reading config from settings file
    config = {
        "lambda": {
            "events": {
                "timeSchedules": [
                    {
                        "ruleName": "unittest-dev-lambda-schedule",
                        "ruleDescription": "run every 1 minute",
                        "scheduleExpression": "rate(1 minute)"
                    }
                ]
            }
        }
    }

    # for time_event in time_event_sources:
    time_event = config['lambda'].get('events', []).get('timeSchedules', [])[0]
    rule_name = time_event.get('ruleName')
    rule_description = time_event.get('ruleDescription')
    schedule_expression = time_event.get('scheduleExpression')

    # now, I need a lambda function that registers the calls!!
    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_counter.py',
                         lambda_handler='handler_counter.handle')
    cleanup_lambdas_deprecated.append(lambda_name)

    # lookup lambda arn
    lambda_client = awsclient.get_client('lambda')
    alias_name = 'ACTIVE'
    lambda_arn = lambda_client.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']
    # create scheduled event source
    rule_arn = _lambda_add_time_schedule_event_source(
        awsclient, rule_name, rule_description, schedule_expression,
        lambda_arn
    )
    _lambda_add_invoke_permission(
        awsclient, lambda_name, 'events.amazonaws.com', rule_arn)

    time.sleep(180)  # wait for at least 2 invocations

    count = _get_count(awsclient, lambda_name)
    assert_greater_equal(int(count), 2)


# DEPRECATED!!
@pytest.mark.aws
@pytest.mark.slow
@check_preconditions
def test_deprecated_wire_unwire_lambda_with_s3(
        awsclient, vendored_folder, cleanup_lambdas_deprecated, cleanup_roles,
        temp_bucket):
    log.info('running test_wire_unwire_lambda_with_s3')

    # create a lambda function
    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_counter.py',
                         lambda_handler='handler_counter.handle')
    cleanup_lambdas_deprecated.append(lambda_name)

    bucket_name = temp_bucket
    config = {
        "lambda": {
            "events": {
                "s3Sources": [
                    {
                        "bucket": bucket_name,
                        "type": "s3:ObjectCreated:*",
                        "suffix": ".gz"
                    }
                ]
            }
        }
    }

    # wire the function with the bucket
    s3_event_sources = config['lambda'].get('events', []).get('s3Sources', [])
    time_event_sources = config['lambda'].get('events', []).get('timeSchedules',
                                                                [])
    exit_code = wire_deprecated(awsclient, lambda_name, s3_event_sources,
                                time_event_sources)
    assert_equal(exit_code, 0)

    # put a file into the bucket
    awsclient.get_client('s3').put_object(
        ACL='public-read',
        Body=b'this is some content',
        Bucket=bucket_name,
        Key='test_file.gz',
    )

    # validate function call
    time.sleep(20)  # sleep till the event arrived
    assert_equal(int(_get_count(awsclient, lambda_name)), 1)

    # unwire the function
    exit_code = unwire_deprecated(awsclient, lambda_name, s3_event_sources,
                                  time_event_sources)
    assert_equal(exit_code, 0)

    # put in another file
    awsclient.get_client('s3').put_object(
        ACL='public-read',
        Body=b'this is some content',
        Bucket=bucket_name,
        Key='test_file_2.gz',
    )

    # validate function not called
    time.sleep(10)
    assert int(_get_count(awsclient, lambda_name)) == 1
