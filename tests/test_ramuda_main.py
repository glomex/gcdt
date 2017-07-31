# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import time
import logging
from tempfile import NamedTemporaryFile

import pytest

from gcdt import utils
from gcdt.ramuda_main import version_cmd, clean_cmd, list_cmd, deploy_cmd, \
    delete_cmd, metrics_cmd, ping_cmd, bundle_cmd, invoke_cmd, logs_cmd
from gcdt_bundler.bundler import bundle

from gcdt_testtools.helpers_aws import check_preconditions, get_tooldata, \
    create_role_helper
from gcdt_testtools.helpers_aws import cleanup_roles  # fixtures!
from gcdt_testtools.helpers_aws import awsclient, temp_bucket  # fixtures!
from .test_ramuda_aws import vendored_folder, temp_lambda, cleanup_lambdas_deprecated  # fixtures!
from gcdt_testtools.helpers import temp_folder, logcapture  # fixtures !
from gcdt_testtools import helpers

# note: xzy_main tests have a more "integrative" character so focus is to make
# sure that the gcdt parts fit together not functional coverage of the parts.
log = logging.getLogger(__name__)


def test_version_cmd(logcapture):
    version_cmd()
    records = list(logcapture.actual())

    assert records[0][1] == 'INFO'
    assert records[0][2].startswith('gcdt version ')
    assert records[1][1] == 'INFO'
    assert records[1][2].startswith('gcdt plugins:')


def test_clean_cmd(temp_folder):
    os.environ['ENV'] = 'DEV'
    paths_to_clean = ['vendored', 'bundle.zip']
    for path in paths_to_clean:
        if path.find('.') != -1:
            open(path, 'a').close()
        else:
            os.mkdir(path)
    clean_cmd()
    for path in paths_to_clean:
        assert not os.path.exists(path)


@pytest.mark.aws
@check_preconditions
def test_list_cmd(awsclient, vendored_folder, temp_lambda, logcapture):
    logcapture.level = logging.INFO
    log.info('running test_list_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'list', config={})

    list_cmd(**tooldata)

    records = list(logcapture.actual())
    assert records[0][1] == 'INFO'
    assert records[0][2] == 'running test_list_cmd'

    assert records[2][1] == 'INFO'
    assert records[2][2].startswith('\tMemory')
    assert records[3][1] == 'INFO'
    assert records[3][2].startswith('\tTimeout')


@pytest.mark.aws
@check_preconditions
def test_deploy_delete_cmds(awsclient, vendored_folder, cleanup_roles,
                            temp_bucket):
    log.info('running test_create_lambda')
    temp_string = utils.random_string()
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
            "name": lambda_name,
            "description": "unittest for ramuda",
            "role": role['Arn'],
            "handlerFunction": "handler.handle",
            "handlerFile": "./resources/sample_lambda/handler.py",
            "timeout": 300,
            "memorySize": 256,
            "events": {
                "s3Sources": [
                    {
                        "bucket": temp_bucket,
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

    tooldata = get_tooldata(awsclient, 'ramuda', 'deploy', config=config)
    tooldata['context']['_arguments'] = {'--keep': False}

    bundle((tooldata['context'], {'ramuda': tooldata['config']}))
    deploy_cmd(False, **tooldata)

    # now we use the delete cmd to remove the lambda function
    tooldata['context']['command'] = 'delete'
    delete_cmd(True, lambda_name, True, **tooldata)


@pytest.mark.aws
@check_preconditions
def test_metrics_cmd(awsclient, vendored_folder, temp_lambda, logcapture):
    logcapture.level = logging.INFO
    log.info('running test_metrics_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'metrics', config={})

    lambda_name = temp_lambda[0]
    metrics_cmd(lambda_name, **tooldata)

    logcapture.check(
        ('tests.test_ramuda_main', 'INFO', u'running test_metrics_cmd'),
        ('gcdt.ramuda_core', 'INFO', u'\tDuration 0'),
        ('gcdt.ramuda_core', 'INFO', u'\tErrors 0'),
        ('gcdt.ramuda_core', 'INFO', u'\tInvocations 0'),
        ('gcdt.ramuda_core', 'INFO', u'\tThrottles 0')
    )


@pytest.mark.aws
@check_preconditions
def test_ping_cmd(awsclient, vendored_folder, temp_lambda, logcapture):
    logcapture.level = logging.INFO
    log.info('running test_ping_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'ping', config={})

    lambda_name = temp_lambda[0]
    ping_cmd(lambda_name, **tooldata)
    logcapture.check(
        ('tests.test_ramuda_main', 'INFO', u'running test_ping_cmd'),
        ('gcdt.ramuda_main', 'INFO', u'Cool, your lambda function did respond to ping with "alive".')
    )


@pytest.mark.aws
@check_preconditions
def test_invoke_cmd(awsclient, vendored_folder, temp_lambda):
    log.info('running test_invoke_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'invoke', config={})

    lambda_name = temp_lambda[0]
    outfile = NamedTemporaryFile(delete=False, dir=None, suffix='').name
    invoke_cmd(lambda_name, None, None, '{"ramuda_action": "ping"}',
               outfile, **tooldata)

    with open(outfile, 'r') as ofile:
        assert ofile.read() == '"alive"'

    # cleanup
    os.unlink(outfile)


def test_bundle_cmd(temp_folder, logcapture):
    tooldata = {
        'context': {'_zipfile': b'some_file'}
    }
    tooldata['context']['_arguments'] = {'--keep': False}
    bundle_cmd(False, **tooldata)
    logcapture.check(
        ('gcdt.ramuda_core', 'INFO', 'Finished - a bundle.zip is waiting for you...')
    )


@pytest.mark.aws
@check_preconditions
def test_logs_cmd(awsclient, vendored_folder, temp_lambda, logcapture):
    logcapture.level = logging.INFO
    log.info('running test_logs_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'logs', config={})
    lambda_name = temp_lambda[0]

    # this testcase is potentially flaky since we depend on the log events
    # to eventually arrive in AWS cloudwatch
    time.sleep(10)  # automatically removed in playback mode!

    logs_cmd(lambda_name, '2m', None, False, **tooldata)
    records = list(logcapture.actual())

    assert records[3][1] == 'INFO'
    assert "{u'ramuda_action': u'ping'}" in records[3][2]
