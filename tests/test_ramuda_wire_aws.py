# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging
import time

import pytest

from gcdt import utils
from gcdt.ramuda_wire import _add_event_source, _remove_event_source, \
    wire, wire_deprecated, unwire, unwire_deprecated, \
    _get_event_source_status, _lambda_add_time_schedule_event_source, _lambda_add_invoke_permission
from gcdt.sns import create_topic, delete_topic, send_message
from gcdt.kinesis import create_stream, describe_stream, delete_stream, \
    wait_for_stream_exists
from gcdt_testtools.helpers_aws import create_lambda_helper, \
    create_lambda_role_helper, check_preconditions
from gcdt_testtools.helpers_aws import temp_bucket, awsclient, \
    cleanup_roles  # fixtures!
from gcdt_testtools.helpers import cleanup_tempfiles, temp_folder  # fixtures!
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

    results = response['Payload'].read()  # payload is a 'StreamingBody'
    return results


@pytest.mark.aws
@pytest.mark.slow
@check_preconditions
def test_wire_unwire_new_events_s3(
        awsclient, vendored_folder, temp_bucket, cleanup_lambdas, cleanup_roles):
    log.info('running test_wire_unwire_new_events_s3')

    # create a lambda function
    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_counter.py',
                         lambda_handler='handler_counter.handle')

    events = [
        {
            "event_source": {
                "arn": "arn:aws:s3:::" + temp_bucket,
                "events": ['s3:ObjectCreated:*'],
                "suffix": ".gz"
            }
        }
    ]
    cleanup_lambdas.append((lambda_name, events))

    # wire the function with the bucket
    exit_code = wire(awsclient, events, lambda_name)
    assert exit_code == 0

    # put a file into the bucket
    awsclient.get_client('s3').put_object(
        ACL='public-read',
        Body=b'this is some content',
        Bucket=temp_bucket,
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
        Bucket=temp_bucket,
        Key='test_file_2.gz',
    )

    # validate function not called
    time.sleep(10)
    assert int(_get_count(awsclient, lambda_name)) == 1


@pytest.mark.aws
@pytest.mark.slow
@check_preconditions
def test_wire_unwire_new_events_sns(
        awsclient, vendored_folder, cleanup_lambdas, cleanup_roles, temp_sns_topic):
    log.info('running test_wire_unwire_new_events_sns')

    # create a lambda function
    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_counter.py',
                         lambda_handler='handler_counter.handle')

    # schedule expressions:
    # http://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html
    events = [
        {
            "event_source": {
                "arn": temp_sns_topic[1],
                "events": [
                    "sns:Publish"
                ]
            }
        }
    ]

    cleanup_lambdas.append((lambda_name, events))

    # wire the function with the bucket
    exit_code = wire(awsclient, events, lambda_name)
    assert exit_code == 0

    assert int(_get_count(awsclient, lambda_name)) == 0

    # send message via sns
    send_message(awsclient, temp_sns_topic[1], {"foo": "bar"})

    time.sleep(10)  # give a little time for the message to arrive
    assert int(_get_count(awsclient, lambda_name)) == 1

    # unwire the function
    exit_code = unwire(awsclient, events, lambda_name)
    assert exit_code == 0


@pytest.mark.aws
@check_preconditions
def test_event_source_lifecycle_s3(awsclient, vendored_folder, temp_lambda, temp_bucket):
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
def test_event_source_lifecycle_sns(awsclient, vendored_folder, temp_lambda, temp_sns_topic):
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
    wait_for_stream_exists(awsclient, temp_string)
    yield temp_string, arn
    # cleanup
    delete_stream(awsclient, temp_string)


@pytest.mark.aws
@check_preconditions
def test_event_source_lifecycle_kinesis(awsclient, vendored_folder, temp_lambda, temp_kinesis):
    log.info('running test_event_source_lifecycle_kinesis')

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


# gcdt tests do not yet support multi-region lambda deployments
'''
@pytest.mark.aws
@check_preconditions
def test_event_source_lifecycle_cloudfront(
        awsclient, vendored_folder, cleanup_lambdas_deprecated, cleanup_roles):
    log.info('running test_event_source_lifecycle_cloudfront')

    lambda_folder = './resources/sample_lambda_edge/'

    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_sample-lambda-edge_' + temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)

    # create the function
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         here(lambda_folder + 'index.js'),
                         lambda_handler='index.handler',
                         folders_from_file=[],
                         runtime='nodejs6.10'
                         )

    cleanup_roles.append(role_name)
    cleanup_lambdas_deprecated.append(lambda_name)

    # lookup lambda arn
    # us-east-1 is the only region that implements lambda@edge
    lambda_client = awsclient.get_client('lambda', region='us-east-1')
    alias_name = 'ACTIVE'
    lambda_arn = lambda_client.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']

    # define event source
    evt_source = {
        "arn": "arn:aws:cloudfront::420189626185:distribution/E1V934UN4EJGJA",
        "cache_behavior": "*",
        "cloudfront_event": "origin-request"
    }

    # event source lifecycle
    _add_event_source(awsclient, evt_source, lambda_arn)
    status = _get_event_source_status(awsclient, evt_source, lambda_arn)
    assert status['EventSourceArn']
    _remove_event_source(awsclient, evt_source, lambda_arn)
'''


@pytest.mark.aws
@check_preconditions
def test_event_source_lifecycle_cloudwatch_pattern(
        awsclient, vendored_folder, cleanup_lambdas_deprecated, cleanup_roles):
    log.info('running test_event_source_lifecycle_cloudwatch_pattern')

    lambda_folder = './resources/sample_lambda_event_pattern/'

    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_sample-lambda-event-pattern_' + temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)

    # create the function
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         here(lambda_folder + 'handler.py'),
                         lambda_handler='handler.handler',
                         folders_from_file=[],
                         runtime='python2.7'
                         )

    cleanup_roles.append(role_name)
    cleanup_lambdas_deprecated.append(lambda_name)

    # lookup lambda arn
    # us-east-1 is the only region that implements lambda@edge
    lambda_client = awsclient.get_client('lambda')
    alias_name = 'ACTIVE'
    lambda_arn = lambda_client.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']

    # define event source
    evt_source = {
        "name": "ssm_parameter_changed",
        "input_path": "$.detail",
        "pattern": {
            "source": [
                "aws.ssm"
            ],
            "detail-type": [
                "Parameter Store Change"
            ]
        }
    }

    # event source lifecycle
    _add_event_source(awsclient, evt_source, lambda_arn)
    status = _get_event_source_status(awsclient, evt_source, lambda_arn)
    assert status['EventSourceArn']
    _remove_event_source(awsclient, evt_source, lambda_arn)


@pytest.mark.aws
@pytest.mark.slow
@check_preconditions
def test_wire_unwire_new_events_cloudwatch_schedule(
        awsclient, vendored_folder, cleanup_lambdas, cleanup_roles):
    log.info('running test_wire_unwire_new_events_cloudwatch_schedule')

    # create a lambda function
    temp_string = utils.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_counter.py',
                         lambda_handler='handler_counter.handle')

    # schedule expressions:
    # http://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html
    events = [
        {
            "event_source": {
                "name": "execute_backup",
                "schedule": "rate(1 minute)"
            }
        }
    ]
    cleanup_lambdas.append((lambda_name, events))

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
def test_event_source_lifecycle_cloudwatch_schedule(awsclient, vendored_folder, temp_lambda):
    log.info('running test_event_source_lifecycle_cloudwatch_schedule')

    lambda_name = temp_lambda[0]

    # lookup lambda arn
    lambda_client = awsclient.get_client('lambda')
    alias_name = 'ACTIVE'
    lambda_arn = lambda_client.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']

    # define event source
    evt_source = {
        "name": "unittest_execute_backup",
        "schedule": "rate(1 minute)"
    }

    # event source lifecycle
    _add_event_source(awsclient, evt_source, lambda_arn)
    status = _get_event_source_status(awsclient, evt_source, lambda_arn)
    assert status['EventSourceArn']
    assert status['State'] == 'ENABLED'
    _remove_event_source(awsclient, evt_source, lambda_arn)


################################################################################
### DEPRECATED
################################################################################
# all test code below is deprecated (related to old ramuda wire implementation)
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
    assert int(count) >= 2


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
    exit_code = unwire_deprecated(awsclient, lambda_name, s3_event_sources,
                                  time_event_sources)
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
