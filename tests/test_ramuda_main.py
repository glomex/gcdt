# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import time
import logging
from tempfile import NamedTemporaryFile

import pytest
from nose.tools import assert_regexp_matches

from gcdt.ramuda_main import version_cmd, clean_cmd, list_cmd, deploy_cmd, \
    delete_cmd, metrics_cmd, ping_cmd, bundle_cmd, invoke_cmd, logs_cmd
from gcdt_bundler.bundler import bundle

from gcdt_testtools.helpers_aws import check_preconditions, get_tooldata, \
    cleanup_roles
from gcdt_testtools.helpers_aws import create_role_helper
from gcdt_testtools.helpers_aws import awsclient, temp_bucket  # fixtures!
from .test_ramuda_aws import vendored_folder, temp_lambda, cleanup_lambdas  # fixtures!
from gcdt_testtools.helpers import temp_folder  # fixtures !
from gcdt_testtools import helpers

# note: xzy_main tests have a more "integrative" character so focus is to make
# sure that the gcdt parts fit together not functional coverage of the parts.
log = logging.getLogger(__name__)


def test_version_cmd(capsys):
    version_cmd()
    out, err = capsys.readouterr()
    assert out.startswith('gcdt version')


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
def test_list_cmd(awsclient, vendored_folder, temp_lambda, capsys):
    log.info('running test_list_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'list', config={})

    lambda_name = temp_lambda[0]
    role_name = temp_lambda[1]

    list_cmd(**tooldata)
    out, err = capsys.readouterr()

    expected_regex = ".*%s\\n\\tMemory: 128\\n\\tTimeout: 300\\n\\tRole: arn:aws:iam::\d{12}:role\/%s\\n\\tCurrent Version: \$LATEST.*" \
                     % (lambda_name, role_name)

    assert_regexp_matches(out.strip(), expected_regex)


@pytest.mark.aws
@check_preconditions
def test_deploy_delete_cmds(awsclient, vendored_folder, cleanup_roles,
                            temp_bucket):
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
def test_metrics_cmd(awsclient, vendored_folder, temp_lambda, capsys):
    log.info('running test_metrics_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'metrics', config={})

    lambda_name = temp_lambda[0]
    metrics_cmd(lambda_name, **tooldata)
    out, err = capsys.readouterr()
    assert_regexp_matches(out.strip(),
                          'Duration 0\\n\\tErrors 0\\n\\tInvocations [0,1]{1}\\n\\tThrottles 0')


@pytest.mark.aws
@check_preconditions
def test_ping_cmd(awsclient, vendored_folder, temp_lambda, capsys):
    log.info('running test_ping_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'ping', config={})

    lambda_name = temp_lambda[0]
    ping_cmd(lambda_name, **tooldata)
    out, err = capsys.readouterr()
    assert '"alive"' in out


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


def test_bundle_cmd(capsys, temp_folder):
    tooldata = {
        'context': {'_zipfile': b'some_file'}
    }
    tooldata['context']['_arguments'] = {'--keep': False}
    bundle_cmd(False, **tooldata)
    out, err = capsys.readouterr()
    assert out == 'Finished - a bundle.zip is waiting for you...\n'


@pytest.mark.aws
@check_preconditions
def test_logs_cmd(awsclient, vendored_folder, temp_lambda, capsys):
    log.info('running test_logs_cmd')
    tooldata = get_tooldata(awsclient, 'ramuda', 'logs', config={})
    lambda_name = temp_lambda[0]

    # this testcase is potentially flaky since we depend on the log events
    # to eventually arrive in AWS cloudwatch
    time.sleep(10)  # automatically removed in playback mode!

    logs_cmd(lambda_name, '2m', None, False, **tooldata)
    out, err = capsys.readouterr()
    # our lambda can handle ping so we should see the related entry in the log
    assert '{u\'ramuda_action\': u\'ping\'}' in out
