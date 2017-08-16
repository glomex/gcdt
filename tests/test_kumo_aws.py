# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
from copy import deepcopy

from nose.tools import assert_equal, assert_false, \
    assert_is_not_none, assert_true
import pytest

from gcdt import utils
from gcdt.kumo_core import load_cloudformation_template, \
    get_parameter_diff, deploy_stack, \
    delete_stack, create_change_set, _get_stack_name, describe_change_set, \
    _get_artifact_bucket, _s3_upload, _get_stack_state, delete_change_set, \
    generate_template, wait_for_stack_delete_complete, wait_for_stack_create_complete, \
    wait_for_stack_update_complete, get_stack_id, stop_stack, start_stack, \
    _stop_ec2_instances, _start_ec2_instances
from gcdt.kumo_util import ensure_ebs_volume_tags_ec2_instance, \
    ensure_ebs_volume_tags_autoscaling_group
from gcdt.utils import are_credentials_still_valid, fix_old_kumo_config, all_pages
from gcdt.servicediscovery import get_outputs_for_stack
from gcdt.s3 import prepare_artifacts_bucket, remove_file_from_s3
from gcdt.gcdt_config_reader import read_json_config

from gcdt_testtools.helpers_aws import check_preconditions, create_role_helper
from gcdt_testtools.helpers_aws import cleanup_buckets, awsclient, \
    cleanup_roles, temp_cloudformation_policy  # fixtures!
from gcdt_testtools import helpers

from . import here


# read template and config
config_simple_stack = fix_old_kumo_config(read_json_config(
    here('resources/simple_cloudformation_stack/gcdt_dev.json')
))['kumo']

# all things are hardcoded here :(
config_ec2 = fix_old_kumo_config(read_json_config(
    here('resources/sample_ec2_cloudformation_stack/gcdt_dev.json')
))['kumo']

config_autoscaling = fix_old_kumo_config(read_json_config(
    here('resources/sample_autoscaling_cloudformation_stack/gcdt_dev.json')
))['kumo']

config_rds_stack = read_json_config(
    here('resources/simple_cloudformation_stack_with_rds/gcdt_dev_lookups.json')
)['kumo']

config_ec2_stack = read_json_config(
    here('resources/simple_cloudformation_stack_with_ec2/gcdt_dev_lookups.json')
)['kumo']


@pytest.fixture(scope='function')  # 'function' or 'module'
def simple_cloudformation_stack(awsclient):
    # create a stack we use for the test lifecycle
    #print_parameter_diff(awsclient, config_simple_stack)
    are_credentials_still_valid(awsclient)
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )
    exit_code = deploy_stack(awsclient, {}, config_simple_stack,
                             cloudformation_simple_stack,
                             override_stack_policy=False)
    assert not exit_code

    yield 'infra-dev-kumo-sample-stack'
    # cleanup
    exit_code = delete_stack(awsclient, config_simple_stack)
    # check whether delete was completed!
    assert not exit_code, 'delete_stack was not completed please make sure to clean up the stack manually'


@pytest.fixture(scope='function')  # 'function' or 'module'
def simple_cloudformation_stack_folder():
    # helper to get into the sample folder so kumo can find cloudformation.py
    cwd = (os.getcwd())
    os.chdir(here('./resources/simple_cloudformation_stack/'))
    yield
    # cleanup
    os.chdir(cwd)  # cd back to original folder


@pytest.fixture(scope='function')  # 'function' or 'module'
def simple_cloudformation_stack_with_rds(awsclient):
    # create a stack we use for the test lifecycle
    stack_name = "infra-dev-kumo-sample-stack-with-rds"
    are_credentials_still_valid(awsclient)
    cloudformation_simple_stack_with_rds, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack_with_rds/cloudformation.py')
    )
    exit_code = deploy_stack(awsclient, {}, config_rds_stack,
                             cloudformation_simple_stack_with_rds,
                             override_stack_policy=False)
    assert not exit_code

    yield stack_name
    # cleanup
    exit_code = delete_stack(awsclient, config_rds_stack)
    # check whether delete was completed!
    assert not exit_code, 'delete_stack was not completed please make sure to clean up the stack manually'


@pytest.fixture(scope='function')  # 'function' or 'module'
def simple_cloudformation_stack_with_ec2(awsclient):
    # create a stack we use for the test lifecycle
    stack_name = "infra-dev-kumo-sample-stack-with-ec2"
    are_credentials_still_valid(awsclient)
    cloudformation_simple_stack_with_rds, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack_with_ec2/cloudformation.py')
    )
    exit_code = deploy_stack(awsclient, {}, config_ec2_stack,
                             cloudformation_simple_stack_with_rds,
                             override_stack_policy=False)
    assert not exit_code
    wait_for_stack_create_complete(awsclient, get_stack_id(awsclient, stack_name))

    yield stack_name
    # cleanup
    exit_code = delete_stack(awsclient, config_ec2_stack)
    # check whether delete was completed!
    assert not exit_code, 'delete_stack was not completed please make sure to clean up the stack manually'


@pytest.fixture(scope='function')  # 'function' or 'module'
def simple_cloudformation_stack_with_rds_folder():
    # helper to get into the sample folder so kumo can find cloudformation.py
    cwd = (os.getcwd())
    os.chdir(here('./resources/simple_cloudformation_stack_with_rds/'))
    yield
    # cleanup
    os.chdir(cwd)  # cd back to original folder


@pytest.fixture(scope='function')  # 'function' or 'module'
def sample_ec2_cloudformation_stack_folder():
    # helper to get into the sample folder so kumo can find cloudformation.py
    cwd = (os.getcwd())
    os.chdir(here('./resources/sample_ec2_cloudformation_stack/'))
    yield
    # cleanup
    os.chdir(cwd)  # cd back to original folder


@pytest.fixture(scope='function')  # 'function' or 'module'
def sample_cloudformation_stack_with_hooks(awsclient):
    # create a stack we use for the test lifecycle
    are_credentials_still_valid(awsclient)
    cloudformation_stack, _ = load_cloudformation_template(
        here('resources/sample_cloudformation_stack_with_hooks/cloudformation.py')
    )
    config_stack = fix_old_kumo_config(read_json_config(
        here('resources/sample_cloudformation_stack_with_hooks/gcdt_dev.json')
    ))['kumo']
    exit_code = deploy_stack(awsclient, {}, config_stack,
                             cloudformation_stack,
                             override_stack_policy=False)
    assert not exit_code

    yield 'infra-dev-kumo-sample-stack-with-hooks'
    # cleanup
    exit_code = delete_stack(awsclient, config_stack)
    # check whether delete was completed!
    assert not exit_code, 'delete_stack was not completed please make sure to clean up the stack manually'


@pytest.mark.aws
@check_preconditions
def test_s3_upload(cleanup_buckets, awsclient):
    #upload_conf = ConfigFactory.parse_file(
    #    here('resources/simple_cloudformation_stack/settings_upload_dev.conf')
    #)

    upload_conf = {
        'stack': {
            'StackName': "infra-dev-kumo-sample-stack",
            'artifactBucket': "unittest-kumo-artifact-bucket"
        },
        'parameters': {
            'InstanceType': "t2.micro"
        }
    }

    region = awsclient.get_client('s3').meta.region_name
    account = os.getenv('ACCOUNT', None)
    # add account prefix to artifact bucket config
    if account:
        upload_conf['stack']['artifactBucket'] = \
            '%s-unittest-kumo-artifact-bucket' % account

    artifact_bucket = _get_artifact_bucket(upload_conf)
    prepare_artifacts_bucket(awsclient, artifact_bucket)
    cleanup_buckets.append(artifact_bucket)
    dest_key = 'kumo/%s/%s-cloudformation.json' % (region,
                                                   _get_stack_name(upload_conf))
    expected_s3url = 'https://s3-%s.amazonaws.com/%s/%s' % (region,
                                                            artifact_bucket,
                                                            dest_key)
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )
    actual_s3url = _s3_upload(awsclient, upload_conf,
                              generate_template({}, upload_conf, cloudformation_simple_stack))
    assert expected_s3url == actual_s3url


# most kumo-operations which rely on a stack on AWS can not be tested in isolation
# since the stack creation for a simple stack takes some time we decided
# to test the stack related operations together

@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_stack_simple_stack(awsclient):
    """Remove the simple_stack stack to cleanup after test run.

    This is intended to be called during test teardown"""
    yield
    # cleanup
    exit_code = delete_stack(awsclient, config_simple_stack)
    # check whether delete was completed!
    assert_false(exit_code, 'delete_stack was not completed\n' +
                 'please make sure to clean up the stack manually')


@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_stack_autoscaling(awsclient):
    """Remove the autoscaling stack to cleanup after test run.

    This is intended to be called during test teardown"""
    yield
    # cleanup
    exit_code = delete_stack(awsclient, config_autoscaling)
    # check whether delete was completed!
    assert_false(exit_code, 'delete_stack was not completed\n' +
                 'please make sure to clean up the stack manually')


@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_stack_ec2(awsclient):
    """Remove the ec2 stack to cleanup after test run.

    This is intended to be called during test teardown"""
    yield
    # cleanup
    exit_code = delete_stack(awsclient, config_ec2)
    # check whether delete was completed!
    assert_false(exit_code, 'delete_stack was not completed\n' +
                 'please make sure to clean up the stack manually')


@pytest.mark.aws
@check_preconditions
def test_kumo_stack_lifecycle(awsclient, simple_cloudformation_stack):
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )

    # preview (with identical stack)
    # TODO: add more asserts!
    change_set_name, stackname, change_set_type = \
        create_change_set(awsclient, {}, config_simple_stack,
                          cloudformation_simple_stack)
    assert stackname == _get_stack_name(config_simple_stack)
    assert change_set_name != ''
    assert change_set_type == 'UPDATE'
    describe_change_set(awsclient, change_set_name, stackname)

    # update the stack
    changed = get_parameter_diff(awsclient, config_simple_stack)
    assert not changed
    exit_code = deploy_stack(awsclient, {}, config_simple_stack,
                             cloudformation_simple_stack,
                             override_stack_policy=False)
    assert exit_code == 0


@pytest.mark.aws
@check_preconditions
def test_kumo_utils_ensure_autoscaling_ebs_tags(cleanup_stack_autoscaling,
                                                awsclient):
    are_credentials_still_valid(awsclient)
    cloudformation_autoscaling, _ = load_cloudformation_template(
        here('resources/sample_autoscaling_cloudformation_stack/cloudformation.py')
    )

    exit_code = deploy_stack(awsclient, {}, config_autoscaling,
                             cloudformation_autoscaling,
                             override_stack_policy=False)
    assert_equal(exit_code, 0)
    stack_name = _get_stack_name(config_autoscaling)
    stack_output = get_outputs_for_stack(awsclient, stack_name)
    as_group_name = stack_output.get('AutoScalingGroupName', None)
    assert_is_not_none(as_group_name)
    tags_v1 = [{'Key': 'kumo-test', 'Value': 'version1'}]
    ensure_ebs_volume_tags_autoscaling_group(awsclient, as_group_name,
                                             tags_v1)

    autoscale_filter = {
        'Name': 'tag:aws:autoscaling:groupName',
        'Values': [as_group_name]
    }
    client_ec2 = awsclient.get_client('ec2')
    response = client_ec2.describe_instances(Filters=[autoscale_filter])
    for r in response['Reservations']:
        for i in r['Instances']:
            volumes = client_ec2.describe_volumes(Filters=[
                {
                    'Name': 'attachment.instance-id',
                    'Values': [i['InstanceId']]
                }
            ])
            for vol in volumes['Volumes']:
                for tag in tags_v1:
                    assert check_volume_tagged(vol, tag)
    tags_v2 = [{'Key': 'kumo-test', 'Value': 'version2'}]
    ensure_ebs_volume_tags_autoscaling_group(awsclient, as_group_name, tags_v2)
    for r in response['Reservations']:
        for i in r['Instances']:
            volumes = client_ec2.describe_volumes(Filters=[
                {
                    'Name': 'attachment.instance-id',
                    'Values': [i['InstanceId']]
                }
            ])
            for vol in volumes['Volumes']:
                for tag in tags_v2:
                    assert_true(check_volume_tagged(vol, tag))
                for tag in tags_v1:
                    assert_false(check_volume_tagged(vol, tag))


@pytest.mark.aws
@check_preconditions
def test_kumo_utils_ensure_ebs_tags(cleanup_stack_ec2, awsclient):
    are_credentials_still_valid(awsclient)
    cloudformation_ec2, _ = load_cloudformation_template(
        here('resources/sample_ec2_cloudformation_stack/cloudformation.py')
    )
    exit_code = deploy_stack(awsclient, {}, config_ec2, cloudformation_ec2,
                             override_stack_policy=False)
    assert_equal(exit_code, 0)

    stack_name = _get_stack_name(config_ec2)
    stack_output = get_outputs_for_stack(awsclient, stack_name)
    instance_id = stack_output.get('InstanceId', None)
    assert_is_not_none(instance_id)
    tags = [{'Key': 'kumo-test', 'Value': 'Success'}]
    ensure_ebs_volume_tags_ec2_instance(awsclient, instance_id, tags)
    client_ec2 = awsclient.get_client('ec2')
    volumes = client_ec2.describe_volumes(Filters=[
        {
            'Name': 'attachment.instance-id',
            'Values': [instance_id]
        }
    ])
    for vol in volumes['Volumes']:
        for tag in tags:
            assert_true(check_volume_tagged(vol, tag))


def check_volume_tagged(vol, tag):
    if 'Tags' in vol:
        if tag in vol['Tags']:
            return True
        else:
            return False
    else:
        return False


@pytest.mark.aws
@check_preconditions
def test_get_stack_state(awsclient, simple_cloudformation_stack):
    state = _get_stack_state(awsclient.get_client('cloudformation'),
                             simple_cloudformation_stack)
    assert state in ['CREATE_IN_PROGRESS', 'CREATE_COMPLETE']


@pytest.mark.aws
@check_preconditions
def test_call_hook(awsclient, sample_cloudformation_stack_with_hooks):
    # note: asserts for parameters are located in the hook
    state = _get_stack_state(awsclient.get_client('cloudformation'),
                             sample_cloudformation_stack_with_hooks)
    assert state in ['CREATE_IN_PROGRESS', 'CREATE_COMPLETE']


@pytest.mark.aws
@check_preconditions
def test_create_stack_rolearn(
        awsclient, cleanup_stack_simple_stack, temp_cloudformation_policy,
        cleanup_roles):
    # create a stack we use for the test lifecycle
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )

    # create role to use for cloudformation deployment
    role = create_role_helper(
        awsclient,
        'unittest_%s_kumo' % utils.random_string(),
        policies=[
            temp_cloudformation_policy,
            'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        ],
        principal_service=['cloudformation.amazonaws.com']
    )
    cleanup_roles.append(role['RoleName'])

    config_rolearn = deepcopy(config_simple_stack)
    config_rolearn['stack']['RoleARN'] = role['Arn']

    exit_code = deploy_stack(awsclient, {}, config_rolearn,
                             cloudformation_simple_stack,
                             override_stack_policy=False)

    assert exit_code == 0


@pytest.mark.aws
@check_preconditions
def test_update_stack_rolearn(awsclient, simple_cloudformation_stack,
                              temp_cloudformation_policy, cleanup_roles):
    # create a stack we use for the test lifecycle
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )

    # create role to use for cloudformation update
    role = create_role_helper(
        awsclient,
        'unittest_%s_kumo' % utils.random_string(),
        policies=[
            temp_cloudformation_policy,
            'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        ],
        principal_service=['cloudformation.amazonaws.com']
    )
    cleanup_roles.append(role['RoleName'])

    config_rolearn = deepcopy(config_simple_stack)
    config_rolearn['stack']['RoleARN'] = role['Arn']

    change_set_name, stackname, change_set_type = \
        create_change_set(awsclient, {}, config_rolearn,
                          cloudformation_simple_stack)
    assert stackname == _get_stack_name(config_rolearn)
    assert change_set_name != ''
    assert change_set_type == 'UPDATE'
    describe_change_set(awsclient, change_set_name, stackname)

    # update the stack
    changed = get_parameter_diff(awsclient, config_rolearn)
    assert not changed
    exit_code = deploy_stack(awsclient, {}, config_rolearn,
                             cloudformation_simple_stack,
                             override_stack_policy=False)
    assert exit_code == 0


@pytest.mark.aws
@check_preconditions
def test_create_update_stack_artifactbucket(awsclient, temp_cloudformation_policy,
                                     cleanup_roles, cleanup_buckets):
    # create a stack we use for the test lifecycle
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )

    upload_conf = {
        'stack': {
            'StackName': "infra-dev-kumo-sample-stack",
            'artifactBucket': "unittest-kumo-artifact-bucket"
        },
        'parameters': {
            'InstanceType': "t2.micro",
        }
    }

    region = awsclient.get_client('s3').meta.region_name
    account = os.getenv('ACCOUNT', None)
    # add account prefix to artifact bucket config
    if account:
        upload_conf['stack']['artifactBucket'] = \
            '%s-unittest-kumo-artifact-bucket' % account

    artifact_bucket = _get_artifact_bucket(upload_conf)
    prepare_artifacts_bucket(awsclient, artifact_bucket)
    cleanup_buckets.append(artifact_bucket)
    dest_key = 'kumo/%s/%s-cloudformation.json' % (region,
                                                   _get_stack_name(upload_conf))
    expected_s3url = 'https://s3-%s.amazonaws.com/%s/%s' % (region,
                                                            artifact_bucket,
                                                            dest_key)
    actual_s3url = _s3_upload(awsclient, upload_conf,
                              generate_template({}, upload_conf, cloudformation_simple_stack))
    assert expected_s3url == actual_s3url

    # create role to use for cloudformation update
    role = create_role_helper(
        awsclient,
        'unittest_%s_kumo' % utils.random_string(),
        policies=[
            temp_cloudformation_policy,
            'arn:aws:iam::aws:policy/AWSCodeDeployReadOnlyAccess',
            'arn:aws:iam::aws:policy/AmazonS3FullAccess'
        ],
        principal_service=['cloudformation.amazonaws.com']
    )
    cleanup_roles.append(role['RoleName'])

    # create
    exit_code = deploy_stack(awsclient, {}, upload_conf,
                             cloudformation_simple_stack,
                             override_stack_policy=False)
    assert exit_code == 0
    stack_id = get_stack_id(awsclient, upload_conf['stack']['StackName'])
    wait_for_stack_create_complete(awsclient, stack_id)

    # update (as a change we add the RoleARN)
    upload_conf['stack']['RoleARN'] = role['Arn']

    # update the stack
    changed = get_parameter_diff(awsclient, upload_conf)
    assert not changed
    exit_code = deploy_stack(awsclient, {}, upload_conf,
                             cloudformation_simple_stack,
                             override_stack_policy=False)
    assert exit_code == 0
    wait_for_stack_update_complete(awsclient, stack_id)

    # cleanup
    exit_code = delete_stack(awsclient, upload_conf)
    assert exit_code == 0
    wait_for_stack_delete_complete(awsclient, stack_id)


@pytest.mark.aws
@check_preconditions
def test_describe_change_set_on_new_stack(awsclient):
    # create a stack we use for the test lifecycle
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )
    change_set_name, stackname, change_set_type = \
        create_change_set(awsclient, {}, config_simple_stack,
                          cloudformation_simple_stack)
    assert stackname == _get_stack_name(config_simple_stack)
    assert change_set_name != ''
    assert change_set_type == 'CREATE'
    describe_change_set(awsclient, change_set_name, stackname)

    # clean up
    # even if we delete the change_Set we need to delete our stack which
    # is in state "REVIEW_IN_PROGRESS"
    awsclient.get_client('cloudformation').delete_stack(
        StackName=stackname,
    )


@pytest.mark.aws
@check_preconditions
def test_kumo_context_contains_stack_output(awsclient):
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )
    context = {}
    exit_code = deploy_stack(awsclient, context, config_simple_stack,
                             cloudformation_simple_stack,
                             override_stack_policy=False)
    assert exit_code == 0
    assert 'stack_output' in context
    assert len(context['stack_output']) == 1
    assert context['stack_output'][0]['Description'] == 'Name of S3 bucket'
    assert context['stack_output'][0]['OutputKey'] == 'BucketName'
    assert context['stack_output'][0]['OutputValue'].startswith('infra-dev-kumo-sample-stack-s3bucket1')

    # cleanup
    exit_code = delete_stack(awsclient, config_simple_stack)
    assert exit_code == 0


@pytest.mark.aws
@check_preconditions
def test_rds_stop_start(awsclient, simple_cloudformation_stack_with_rds,
                        simple_cloudformation_stack_with_rds_folder):
    assert stop_stack(awsclient, config_rds_stack) == 0
    assert start_stack(awsclient, config_rds_stack) == 0


@pytest.mark.aws
@check_preconditions
def test_ec2_instance_stop_start(awsclient, simple_cloudformation_stack_with_ec2):
    def _get_instance_status(ec2_instance):
        # helper to check the status
        client_ec2 = awsclient.get_client('ec2')
        instances_status = all_pages(
            client_ec2.describe_instance_status,
            {
                'InstanceIds': [ec2_instance],
                'IncludeAllInstances': True
            },
            lambda r: [i['InstanceState']['Name'] for i in r.get('InstanceStatuses', [])],
        )[0]
        return instances_status

    stack_name = _get_stack_name(config_ec2_stack)
    client_cfn = awsclient.get_client('cloudformation')
    resources = all_pages(
        client_cfn.list_stack_resources,
        { 'StackName': stack_name },
        lambda r: r['StackResourceSummaries']
    )
    instances = [
        r['PhysicalResourceId'] for r in resources
        if r['ResourceType'] == 'AWS::EC2::Instance'
    ]
    assert _get_instance_status(instances[0]) == 'running'

    _stop_ec2_instances(awsclient, instances, wait=True)
    assert _get_instance_status(instances[0]) == 'stopped'

    _start_ec2_instances(awsclient, instances, wait=True)
    assert _get_instance_status(instances[0]) == 'running'
