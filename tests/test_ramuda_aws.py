# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging
import shutil
import time

import os
import pytest
from gcdt_bundler.bundler import get_zipped_file
from nose.tools import assert_equal, assert_greater_equal, \
    assert_in, assert_not_in, assert_regexp_matches

from gcdt.ramuda_core import delete_lambda, deploy_lambda, ping, \
    _lambda_add_time_schedule_event_source, \
    wire, unwire, _lambda_add_invoke_permission, list_functions, \
    _update_lambda_configuration, get_metrics, rollback, _get_alias_version, \
    info, invoke
from gcdt.ramuda_utils import list_lambda_versions, create_sha256, \
    get_remote_code_hash
from gcdt_testtools import helpers
from gcdt_testtools.helpers import create_tempfile
from gcdt_testtools.helpers_aws import create_role_helper, delete_role_helper, \
    create_lambda_helper, create_lambda_role_helper, check_preconditions, \
    settings_requirements, check_normal_mode
from gcdt_testtools.helpers_aws import temp_bucket, awsclient, cleanup_roles  # fixtures!
from gcdt_testtools.helpers import cleanup_tempfiles, temp_folder  # fixtures!
from gcdt_testtools.helpers import create_tempfile
from . import here

log = logging.getLogger(__name__)


def get_size(start_path='.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


# TODO: move AWS resource helpers to helpers_aws.py
# TODO: if we use this we need to move some of the following code to
# TODO: helpers_was.py!


@pytest.fixture(scope='function')  # 'function' or 'module'
def vendored_folder():
    # provide a temp folder and cleanup after test
    # this also changes into the folder and back to cwd during cleanup
    cwd = (os.getcwd())
    folder = here('.')
    os.chdir(folder)  # reuse ./vendored folder => cd tests/
    settings_requirements()
    yield
    # cleanup
    os.chdir(cwd)  # cd to original folder
    # reuse ./vendored folder


@pytest.fixture(scope='function')  # 'function' or 'module'
def temp_lambda(awsclient):
    # provide a lambda function and cleanup after test suite
    temp_string = helpers.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    # create the function
    role_arn = create_lambda_role_helper(awsclient, role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         # './resources/sample_lambda/handler.py',
                         here('./resources/sample_lambda/handler.py'),
                         lambda_handler='handler.handle')
    yield lambda_name, role_name, role_arn
    # cleanup
    delete_lambda(awsclient, lambda_name)
    delete_role_helper(awsclient, role_name)


@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_lambdas(awsclient):
    items = []
    yield items
    # cleanup
    for i in items:
        delete_lambda(awsclient, i)


@pytest.mark.aws
@check_preconditions
def test_create_lambda(awsclient, vendored_folder, cleanup_lambdas,
                       cleanup_roles):
    log.info('running test_create_lambda')
    temp_string = helpers.random_string()
    lambda_name = 'jenkins_test_' + temp_string
    log.info(lambda_name)
    role = create_role_helper(
        awsclient,
        'unittest_%s_lambda' % temp_string,
        policies=[
            'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole',
            'arn:aws:iam::aws:policy/AWSLambdaExecute']
    )
    cleanup_roles.append(role['RoleName'])

    config = {
        "lambda": {
            "name": "dp-dev-sample-lambda-jobr1",
            "description": "lambda test for ramuda",
            "role": "'unused'",
            "handlerFunction": "handler.handle",
            "handlerFile": "./resources/sample_lambda/handler.py",
            "timeout": 300,
            "memorySize": 256,
            "events": {
                "s3Sources": [
                    {
                        "bucket": "jobr-test",
                        "type": "s3:ObjectCreated:*",
                        "suffix": ".gz"
                    }
                ],
                "timeSchedules": [
                    {
                        "ruleName": "infra-dev-sample-lambda-jobr-T1",
                        "ruleDescription": "run every 5 min from 0-5",
                        "scheduleExpression": "cron(0/5 0-5 ? * * *)"
                    },
                    {
                        "ruleName": "infra-dev-sample-lambda-jobr-T2",
                        "ruleDescription": "run every 5 min from 8-23:59",
                        "scheduleExpression": "cron(0/5 8-23:59 ? * * *)"
                    }
                ]
            },
            "vpc": {
                "subnetIds": [
                    "subnet-d5ffb0b1",
                    "subnet-d5ffb0b1",
                    "subnet-d5ffb0b1",
                    "subnet-e9db9f9f"
                ],
                "securityGroups": [
                    "sg-660dd700"
                ]
            }
        },
        "bundling": {
            "zip": "bundle.zip",
            "folders": [
                {
                    "source": "./vendored",
                    "target": "."
                },
                {
                    "source": "./impl",
                    "target": "impl"
                }
            ]
        },
        "deployment": {
            "region": "eu-west-1"
        }
    }
    lambda_description = config['lambda'].get('description')
    # print (role)
    role_arn = role['Arn']
    lambda_handler = config['lambda'].get('handlerFunction')
    handler_filename = config['lambda'].get('handlerFile')
    timeout = int(config['lambda'].get('timeout'))
    memory_size = int(config['lambda'].get('memorySize'))
    zip_name = config['bundling'].get('zip')
    folders_from_file = config['bundling'].get('folders')
    subnet_ids = config['lambda'].get('vpc', {}).get('subnetIds', None)
    security_groups = config['lambda'].get('vpc', {}).get('securityGroups', None)
    region = config['deployment'].get('region')
    artifact_bucket = config['deployment'].get('artifactBucket', None)

    zipfile = get_zipped_file(
        handler_filename,
        folders_from_file,
        )

    deploy_lambda(
        awsclient=awsclient,
        function_name=lambda_name,
        role=role_arn,
        handler_filename=handler_filename,
        handler_function=lambda_handler,
        folders=folders_from_file,
        description=lambda_description,
        timeout=timeout,
        memory=memory_size,
        artifact_bucket=artifact_bucket,
        zipfile=zipfile
    )
    # TODO improve this (by using a waiter??)
    cleanup_lambdas.append(lambda_name)


@pytest.mark.aws
@check_preconditions
@pytest.mark.parametrize('runtime', ['nodejs4.3', 'nodejs6.10'])
def test_create_lambda_nodejs(runtime, awsclient, temp_folder, cleanup_lambdas,
                              cleanup_roles):
    log.info('running test_create_lambda_nodejs')
    # copy package.json and settings_dev.conf from sample
    shutil.copy(
        here('./resources/sample_lambda_nodejs/index.js'), temp_folder[0])
    shutil.copy(
        here('./resources/sample_lambda_nodejs/package.json'), temp_folder[0])
    shutil.copy(
        here('./resources/sample_lambda_nodejs/settings_dev.conf'),
        temp_folder[0])
    temp_string = helpers.random_string()
    lambda_name = 'jenkins_test_' + temp_string
    log.info(lambda_name)
    role = create_role_helper(
        awsclient,
        'unittest_%s_lambda' % temp_string,
        policies=[
            'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole',
            'arn:aws:iam::aws:policy/AWSLambdaExecute']
    )
    cleanup_roles.append(role['RoleName'])

    config = {
        "lambda": {
            "runtime": runtime,  # "nodejs4.3",
            "name": "infra-dev-sample-lambda-jobr1",
            "description": "lambda test for ramuda",
            "role": "'unused'",
            "handlerFunction": "index.handler",
            "handlerFile": "index.js",
            "timeout": 300,
            "memorySize": 256,
            "events": {
                "s3Sources": [
                    {
                        "bucket": "jobr-test",
                        "type": "s3:ObjectCreated:*",
                        "suffix": ".gz"
                    }
                ],
                "timeSchedules": [
                    {
                        "ruleName": "infra-dev-sample-lambda-jobr-T1",
                        "ruleDescription": "run every 5 min from 0-5",
                        "scheduleExpression": "cron(0/5 0-5 ? * * *)"
                    },
                    {
                        "ruleName": "infra-dev-sample-lambda-jobr-T2",
                        "ruleDescription": "run every 5 min from 8-23:59",
                        "scheduleExpression": "cron(0/5 8-23:59 ? * * *)"
                    }
                ]
            },
            "vpc": {
                "subnetIds": [
                    "subnet-d5ffb0b1",
                    "subnet-d5ffb0b1",
                    "subnet-d5ffb0b1",
                    "subnet-e9db9f9f"
                ],
                "securityGroups": [
                    "sg-660dd700"
                ]
            }
        },
        "bundling": {
            "zip": "bundle.zip",
            "folders": [
                {
                    "source": "./node_modules",
                    "target": "node_modules"
                }
            ]
        },
        "deployment": {
            "region": "eu-west-1"
        }
    }
    runtime = config['lambda'].get('runtime')
    lambda_description = config['lambda'].get('description')
    # print (role)
    role_arn = role['Arn']
    lambda_handler = config['lambda'].get('handlerFunction')
    handler_filename = config['lambda'].get('handlerFile')
    timeout = int(config['lambda'].get('timeout'))
    memory_size = int(config['lambda'].get('memorySize'))
    zip_name = config['bundling'].get('zip')
    folders_from_file = config['bundling'].get('folders')
    subnet_ids = config['lambda'].get('vpc', {}).get('subnetIds', None)
    security_groups = config['lambda'].get('vpc', {}).get('securityGroups', None)
    region = config['deployment'].get('region')
    artifact_bucket = config['deployment'].get('artifactBucket', None)

    zipfile = get_zipped_file(
        handler_filename,
        folders_from_file,
        runtime=runtime,
    )

    deploy_lambda(
        awsclient=awsclient,
        function_name=lambda_name,
        role=role_arn,
        handler_filename=handler_filename,
        handler_function=lambda_handler,
        folders=folders_from_file,
        description=lambda_description,
        timeout=timeout,
        memory=memory_size,
        artifact_bucket=artifact_bucket,
        zipfile=zipfile,
        runtime=runtime
    )
    # TODO improve this (by using a waiter??)
    cleanup_lambdas.append(lambda_name)


@pytest.mark.aws
@check_preconditions
def test_create_lambda_with_s3(awsclient, vendored_folder, cleanup_lambdas,
                               cleanup_roles):
    log.info('running test_create_lambda_with_s3')
    account = os.getenv('ACCOUNT')
    temp_string = helpers.random_string()
    lambda_name = 'jenkins_test_' + temp_string
    log.info(lambda_name)
    role = create_role_helper(
        awsclient,
        'unittest_%s_lambda' % temp_string,
        policies=[
            'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole',
            'arn:aws:iam::aws:policy/AWSLambdaExecute']
    )
    cleanup_roles.append(role['RoleName'])

    config = {
        "lambda": {
            "name": "dp-dev-sample-lambda-jobr1",
            "description": "lambda nodejs test for ramuda",
            "handlerFunction": "handler.handle",
            "handlerFile": "./resources/sample_lambda/handler.py",
            "timeout": 300,
            "memorySize": 256,
            "events": {
                "s3Sources": [
                    {
                        "bucket": "jobr-test",
                        "type": "s3:ObjectCreated:*",
                        "suffix": ".gz"
                    }
                ],
                "timeSchedules": [
                    {
                        "ruleName": "infra-dev-sample-lambda-jobr-T1",
                        "ruleDescription": "run every 5 min from 0-5",
                        "scheduleExpression": "cron(0/5 0-5 ? * * *)"
                    },
                    {
                        "ruleName": "infra-dev-sample-lambda-jobr-T2",
                        "ruleDescription": "run every 5 min from 8-23:59",
                        "scheduleExpression": "cron(0/5 8-23:59 ? * * *)"
                    }
                ]
            },
            "vpc": {
                "subnetIds": [
                    "subnet-d5ffb0b1",
                    "subnet-d5ffb0b1",
                    "subnet-d5ffb0b1",
                    "subnet-e9db9f9f"
                ],
                "securityGroups": [
                    "sg-660dd700"
                ]
            }
        },
        "bundling": {
            "zip": "bundle.zip",
            "folders": [
                {
                    "source": "./vendored",
                    "target": "."
                },
                {
                    "source": "./impl",
                    "target": "impl"
                }
            ]
        },
        "deployment": {
            "region": "eu-west-1",
            "artifactBucket": "7finity-%s-dev-deployment" % account
        }
    }
    lambda_description = config['lambda'].get('description')
    # print (role)
    role_arn = role['Arn']
    lambda_handler = config['lambda'].get('handlerFunction')
    handler_filename = config['lambda'].get('handlerFile')
    timeout = int(config['lambda'].get('timeout'))
    memory_size = int(config['lambda'].get('memorySize'))
    zip_name = config['bundling'].get('zip')
    folders_from_file = config['bundling'].get('folders')
    subnet_ids = config['lambda'].get('vpc', {}).get('subnetIds', None)
    security_groups = config['lambda'].get('vpc', {}).get('securityGroups', None)
    region = config['deployment'].get('region')
    artifact_bucket = config['deployment'].get('artifactBucket', None)

    zipfile = get_zipped_file(
        handler_filename,
        folders_from_file,
    )

    deploy_lambda(
        awsclient=awsclient,
        function_name=lambda_name,
        role=role_arn,
        handler_filename=handler_filename,
        handler_function=lambda_handler,
        folders=folders_from_file,
        description=lambda_description,
        timeout=timeout,
        memory=memory_size,
        artifact_bucket=artifact_bucket,
        zipfile=zipfile
    )
    cleanup_lambdas.append(lambda_name)


@pytest.mark.aws
@check_preconditions
def test_update_lambda(awsclient, vendored_folder, cleanup_lambdas,
                       cleanup_roles):
    log.info('running test_update_lambda')
    temp_string = helpers.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    # create the function
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler.py')
    # update the function
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_v2.py')
    cleanup_lambdas.append(lambda_name)


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
@check_preconditions
def test_schedule_event_source(awsclient, vendored_folder, cleanup_lambdas,
                               cleanup_roles):
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
    temp_string = helpers.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_counter.py',
                         lambda_handler='handler_counter.handle')
    cleanup_lambdas.append(lambda_name)

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


@pytest.mark.aws
@pytest.mark.slow
@check_preconditions
def test_wire_unwire_lambda_with_s3(awsclient, vendored_folder,
                                    cleanup_lambdas, cleanup_roles,
                                    temp_bucket):
    log.info('running test_wire_unwire_lambda_with_s3')

    # create a lambda function
    temp_string = helpers.random_string()
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_counter.py',
                         lambda_handler='handler_counter.handle')
    cleanup_lambdas.append(lambda_name)

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
    time_event_sources = config['lambda'].get('events', []).get('timeSchedules', [])
    exit_code = wire(awsclient, lambda_name, s3_event_sources,
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
    exit_code = unwire(awsclient, lambda_name, s3_event_sources,
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


@pytest.mark.aws
@check_preconditions
def test_lambda_add_invoke_permission(awsclient, vendored_folder,
                                      temp_bucket, cleanup_lambdas,
                                      cleanup_roles):
    log.info('running test_lambda_add_invoke_permission')
    temp_string = helpers.random_string()
    # print(temp_string)
    lambda_name = 'jenkins_test_%s' % temp_string
    role_name = 'unittest_%s_lambda' % temp_string
    role_arn = create_lambda_role_helper(awsclient, role_name)
    cleanup_roles.append(role_name)
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_counter.py',
                         lambda_handler='handler_counter.handle')
    cleanup_lambdas.append(lambda_name)
    bucket_name = temp_bucket

    s3_arn = 'arn:aws:s3:::' + bucket_name
    response = _lambda_add_invoke_permission(
        awsclient, lambda_name, 's3.amazonaws.com', s3_arn)

    # {"Statement":"{\"Condition\":{\"ArnLike\":{\"AWS:SourceArn\":\"arn:aws:s3:::unittest-lambda-s3-bucket-coedce\"}},\"Action\":[\"lambda:InvokeFunction\"],\"Resource\":\"arn:aws:lambda:eu-west-1:188084614522:function:jenkins_test_coedce:ACTIVE\",\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"s3.amazonaws.com\"},\"Sid\":\"07c77fac-68ff-11e6-97f8-c4850848610b\"}"}

    assert_not_in('Error', response)
    assert_in('lambda:InvokeFunction', response['Statement'])
    # TODO add more asserts!!


@pytest.mark.aws
@check_preconditions
def test_list_functions(awsclient, vendored_folder, temp_lambda, capsys):
    log.info('running test_list_functions')

    lambda_name = temp_lambda[0]
    role_name = temp_lambda[1]

    list_functions(awsclient)
    out, err = capsys.readouterr()

    expected_regex = ".*%s\\n\\tMemory: 128\\n\\tTimeout: 300\\n\\tRole: arn:aws:iam::\d{12}:role\/%s\\n\\tCurrent Version: \$LATEST.*" \
                     % (lambda_name, role_name)

    assert_regexp_matches(out.strip(), expected_regex)


@pytest.mark.aws
@check_preconditions
def test_update_lambda_configuration(awsclient, vendored_folder, temp_lambda):
    log.info('running test_update_lambda_configuration')

    lambda_name = temp_lambda[0]
    role_arn = temp_lambda[2]
    handler_function = './resources/sample_lambda/handler_counter.py'
    lambda_description = 'lambda created for unittesting ramuda deployment'

    timeout = 300
    memory_size = 256
    function_version = _update_lambda_configuration(awsclient, lambda_name,
                                                    role_arn, handler_function,
                                                    lambda_description, timeout,
                                                    memory_size)
    assert_equal(function_version, '$LATEST')


@pytest.mark.aws
@check_preconditions
def test_get_metrics(awsclient, vendored_folder, temp_lambda, capsys):
    log.info('running test_get_metrics')

    get_metrics(awsclient, temp_lambda[0])
    out, err = capsys.readouterr()
    assert_regexp_matches(out.strip(),
                          'Duration 0\\n\\tErrors 0\\n\\tInvocations [0,1]{1}\\n\\tThrottles 0')


@pytest.mark.aws
@check_preconditions
def test_rollback(awsclient, vendored_folder, temp_lambda):
    log.info('running test_rollback')

    lambda_name = temp_lambda[0]
    role_arn = temp_lambda[2]
    alias_version = _get_alias_version(awsclient, lambda_name, 'ACTIVE')
    assert_equal(alias_version, '1')

    # update the function
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_v2.py')

    # now we use function_version 2!
    alias_version = _get_alias_version(awsclient, lambda_name, 'ACTIVE')
    assert_equal(alias_version, '$LATEST')

    exit_code = rollback(awsclient, lambda_name, alias_name='ACTIVE')
    assert_equal(exit_code, 0)

    # we rolled back to function_version 1
    alias_version = _get_alias_version(awsclient, lambda_name, 'ACTIVE')
    assert_equal(alias_version, '1')

    # try to rollback when previous version does not exist
    exit_code = rollback(awsclient, lambda_name, alias_name='ACTIVE')
    assert_equal(exit_code, 1)

    # version did not change
    alias_version = _get_alias_version(awsclient, lambda_name, 'ACTIVE')
    assert_equal(alias_version, '1')

    # roll back to the latest version
    exit_code = rollback(awsclient, lambda_name, alias_name='ACTIVE',
                         version='$LATEST')
    assert_equal(exit_code, 0)

    # latest version of lambda is used
    alias_version = _get_alias_version(awsclient, lambda_name, 'ACTIVE')
    assert_equal(alias_version, '$LATEST')

    # TODO: create more versions >5
    # TODO: do multiple rollbacks >5
    # TODO: verify version + active after rollback
    # TODO: verify invocations meet the right lamda_function version

    # here we have the test for ramuda_utils.list_lambda_versions
    response = list_lambda_versions(awsclient, lambda_name)
    assert_equal(response['Versions'][0]['Version'], '$LATEST')
    assert_equal(response['Versions'][1]['Version'], '1')
    assert_equal(response['Versions'][2]['Version'], '2')


@pytest.mark.aws
@check_preconditions
@check_normal_mode
def test_get_remote_code_hash(awsclient, vendored_folder, temp_lambda):
    # this works only with the '--keep' option so timestamps of installed
    # dependencies are unchanged. Consequently in this situation the bundle
    # hashcode is the same.
    # NOTE: this only makes sense in 'normal' placebo mode (not with playback!)
    log.info('running test_get_remote_code_hash')

    handler_filename = './resources/sample_lambda/handler.py'
    folders_from_file = [
        {'source': './vendored', 'target': '.'},
        {'source': './resources/sample_lambda/impl', 'target': 'impl'}
    ]

    # now run the update using '--keep' option to get a similar hash
    # get local hash
    zipfile = get_zipped_file(handler_filename, folders_from_file, keep=True)

    expected_hash = create_sha256(zipfile)

    lambda_name = temp_lambda[0]
    time.sleep(10)
    remote_hash = get_remote_code_hash(awsclient, lambda_name)
    assert remote_hash == expected_hash


@pytest.mark.aws
@check_preconditions
def test_ping(awsclient, vendored_folder, temp_lambda):
    log.info('running test_ping')

    lambda_name = temp_lambda[0]
    role_arn = temp_lambda[2]

    # test the ping
    response = ping(awsclient, lambda_name)
    assert response == '"alive"'

    # update the function
    create_lambda_helper(awsclient, lambda_name, role_arn,
                         './resources/sample_lambda/handler_no_ping.py',
                         lambda_handler='handler_no_ping.handle')

    # test has no ping
    response = ping(awsclient, lambda_name)
    assert response == '{"ramuda_action": "ping"}'


@pytest.mark.aws
@check_preconditions
def test_invoke_outfile(awsclient, vendored_folder, temp_lambda):
    log.info('running test_invoke')

    lambda_name = temp_lambda[0]
    role_arn = temp_lambda[2]
    outfile = create_tempfile('')
    payload = '{"ramuda_action": "ping"}'  # default to ping event

    response = invoke(awsclient, lambda_name, payload=payload, outfile=outfile)

    with open(outfile, 'r') as ofile:
        assert ofile.read() == '"alive"'

    # cleanup
    os.unlink(outfile)


@pytest.mark.aws
@check_preconditions
def test_invoke_payload_from_file(awsclient, vendored_folder, temp_lambda):
    log.info('running test_invoke')

    lambda_name = temp_lambda[0]
    role_arn = temp_lambda[2]
    payload_file = create_tempfile('{"ramuda_action": "ping"}')

    response = invoke(awsclient, lambda_name, payload='file:/%s' % payload_file)
    assert response == '"alive"'

    # cleanup
    os.unlink(payload_file)


@pytest.mark.aws
@check_preconditions
def test_info(awsclient, vendored_folder, temp_lambda, capsys):
    function_name = temp_lambda[0]
    info(awsclient, function_name)
    out, err = capsys.readouterr()
    assert '### PERMISSIONS ###' in out
    assert '### EVENT SOURCES ###' in out

# TODO test_info with s3 and timed event sources
# TODO
# _ensure_cloudwatch_event
# wire
# _get_lambda_policies
#
