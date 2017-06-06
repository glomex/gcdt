# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import logging

from nose.tools import assert_equal, assert_false
import pytest
from gcdt_bundler.bundler import bundle_revision

from gcdt.kumo_core import deploy_stack, load_cloudformation_template, delete_stack, _get_stack_name
from gcdt.utils import are_credentials_still_valid
from gcdt.servicediscovery import get_outputs_for_stack
from gcdt.tenkai_core import deploy as tenkai_deploy, deployment_status
from gcdt.gcdt_config_reader import read_json_config
from gcdt_testtools.helpers_aws import check_preconditions
from gcdt_testtools.helpers_aws import cleanup_buckets, awsclient  # fixtures!
from . import here

log = logging.getLogger(__name__)


# read config
config_sample_codeploy_stack = read_json_config(
    here('resources/sample_codedeploy_app/gcdt_dev.json')
)['kumo']


@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_stack_tenkai(awsclient):
    """Remove the ec2 stack to cleanup after test run.

    This is intended to be called during test teardown"""
    yield
    # cleanup
    exit_code = delete_stack(awsclient, config_sample_codeploy_stack)
    # check whether delete was completed!
    assert_false(exit_code, 'delete_stack was not completed\n' +
                 'please make sure to clean up the stack manually')


@pytest.fixture(scope='function')  # 'function' or 'module'
def sample_codedeploy_app(awsclient):
    are_credentials_still_valid(awsclient)
    # Set up stack with an ec2 and deployment
    cloudformation, _ = load_cloudformation_template(
        here('resources/sample_codedeploy_app/cloudformation.py')
    )
    exit_code = deploy_stack(awsclient, config_sample_codeploy_stack,
                             cloudformation, override_stack_policy=False)
    assert_equal(exit_code, 0)

    yield
    # cleanup
    exit_code = delete_stack(awsclient, config_sample_codeploy_stack)
    # check whether delete was completed!
    assert_false(exit_code, 'delete_stack was not completed\n' +
                 'please make sure to clean up the stack manually')


@pytest.mark.aws
@check_preconditions
def test_tenkai_exit_codes(cleanup_stack_tenkai, awsclient):
    are_credentials_still_valid(awsclient)
    # Set up stack with an ec2 and deployment
    cloudformation, _ = load_cloudformation_template(
        here('resources/sample_codedeploy_app/cloudformation.py')
    )
    exit_code = deploy_stack(awsclient, config_sample_codeploy_stack,
                             cloudformation, override_stack_policy=False)
    assert_equal(exit_code, 0)

    stack_name = _get_stack_name(config_sample_codeploy_stack)
    stack_output = get_outputs_for_stack(awsclient, stack_name)
    app_name = stack_output.get('ApplicationName', None)
    deployment_group = stack_output.get('DeploymentGroupName', None)
    cwd = here('.')

    not_working_deploy_dir = here(
        './resources/sample_codedeploy_app/not_working')
    working_deploy_dir = here('./resources/sample_codedeploy_app/working')
    os.chdir(not_working_deploy_dir)
    folders = [{'source': 'codedeploy', 'target': ''}]

    # test deployment which should exit with exit code 1
    deploy_id_1 = tenkai_deploy(
        awsclient,
        app_name,
        deployment_group,
        'CodeDeployDefault.AllAtOnce',
        '7finity-infra-dev-deployment',
        bundle_revision(folders)
    )
    exit_code = deployment_status(awsclient, deploy_id_1)
    assert exit_code == 1

    # test deployment which should exit with exit code 0
    os.chdir(working_deploy_dir)
    deploy_id_2 = tenkai_deploy(
        awsclient,
        app_name,
        deployment_group,
        'CodeDeployDefault.AllAtOnce',
        '7finity-infra-dev-deployment',
        bundle_revision(folders)
    )
    exit_code = deployment_status(awsclient, deploy_id_2)
    assert exit_code == 0
    os.chdir(cwd)
