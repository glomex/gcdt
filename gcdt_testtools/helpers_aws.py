# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import time
import json
import textwrap
import logging

import botocore.session
import pytest
from awacs.aws import Action, Allow, Policy, Principal, Statement

from gcdt import utils
from gcdt.ramuda_core import deploy_lambda
from gcdt.s3 import create_bucket, delete_bucket
from gcdt_testtools import helpers
from .placebo_awsclient import PlaceboAWSClient
from gcdt import __version__
from gcdt.gcdt_config_reader import read_json_config
from gcdt.utils import get_env, fix_old_kumo_config

log = logging.getLogger(__name__)


@pytest.fixture(scope='function')  # 'function' or 'module'
def temp_bucket(awsclient):
    # create a bucket
    temp_string = utils.random_string()
    bucket_name = 'unittest-lambda-s3-event-source-%s' % temp_string
    create_bucket(awsclient, bucket_name)
    yield bucket_name
    # cleanup
    delete_bucket(awsclient, bucket_name)


@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_buckets(awsclient):
    items = []
    yield items
    # cleanup
    for i in items:
        delete_bucket(awsclient, i)


# lambda helpers
def create_lambda_role_helper(awsclient, role_name):
    # caller needs to clean up both role!
    role = create_role_helper(
        awsclient, role_name,
        policies=[
            'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole',
            'arn:aws:iam::aws:policy/AWSLambdaExecute',
            'arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole'
        ]
    )
    return role['Arn']


def settings_requirements():
    settings_file = os.path.join('settings_dev.conf')
    with open(settings_file, 'w') as settings:
        setting_string = textwrap.dedent("""\
            sample_lambda {
                cw_name = "dp-dev-sample"
            }""")
        settings.write(setting_string)
    requirements_txt = os.path.join('requirements.txt')
    with open(requirements_txt, 'w') as req:
        req.write('pyhocon==0.3.28\n')
    # ./vendored folder
    if not os.path.exists('./vendored'):
        # reuse ./vendored folder to save us some time during pip install...
        os.makedirs('./vendored')


def create_lambda_helper(awsclient, lambda_name, role_arn, handler_filename,
                         lambda_handler='handler.handle',
                         folders_from_file=None,
                         **kwargs):
    """
    NOTE: caller needs to clean up both lambda!

    :param awsclient:
    :param lambda_name:
    :param role_arn:
    :param handler_filename:
    :param lambda_handler:
    :param folders_from_file:
    :param kwargs: additional kwargs are used in deploy_lambda
    :return:
    """
    from gcdt_bundler.bundler import get_zipped_file
    settings_requirements()

    lambda_description = 'lambda created for unittesting ramuda deployment'
    timeout = 300
    memory_size = 128
    if not folders_from_file:
        folders_from_file = [
            {'source': './vendored', 'target': '.'},
            {'source': './resources/sample_lambda/impl', 'target': 'impl'}
        ]
    artifact_bucket = None

    zipfile = get_zipped_file(
        handler_filename,
        folders_from_file,
    )

    # create the AWS Lambda function
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
        **kwargs
    )

    # TODO better use waiter for that!
    time.sleep(10)


# role helpers
def delete_role_helper(awsclient, role_name):
    """Delete the testing role.

    :param awsclient:
    :param role_name: the temporary role that has been created via _create_role
    """
    # role_name = role['RoleName']
    iam = awsclient.get_client('iam')
    roles = [r['RoleName'] for r in iam.list_roles()['Roles']]
    if role_name in roles:
        # detach all policies first
        policies = iam.list_attached_role_policies(RoleName=role_name)
        for p in policies['AttachedPolicies']:
            response = iam.detach_role_policy(
                RoleName=role_name,
                PolicyArn=p['PolicyArn']
            )

        # delete the role
        response = iam.delete_role(RoleName=role_name)


def create_role_helper(awsclient, name, policies=None, principal_service=None):
    """Create a role with an optional inline policy """
    iam = awsclient.get_client('iam')
    policy_doc = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Effect': 'Allow',
                'Principal': {'Service': ['lambda.amazonaws.com']},
                'Action': ['sts:AssumeRole']
            },
        ]
    }
    if principal_service:
        policy_doc['Statement'][0]['Principal']['Service'] = principal_service
    roles = [r['RoleName'] for r in iam.list_roles()['Roles']]
    if name in roles:
        print('IAM role %s exists' % name)
        role = iam.get_role(RoleName=name)['Role']
    else:
        print('Creating IAM role %s' % name)
        role = iam.create_role(
            RoleName=name,
            AssumeRolePolicyDocument=json.dumps(policy_doc)
        )['Role']

    # attach managed policy
    if policies is not None:
        for p in policies:
            iam.attach_role_policy(RoleName=role['RoleName'], PolicyArn=p)

    # TODO: on 20160816 we had multiple times that the role could not be assigned
    # we suspect that this is a timing issue with AWS lambda
    # get_role to make sure role is available for lambda
    # response = iam.list_attached_role_policies(RoleName=name)
    # log.info('created role: %s' % name)
    # log.info(response)
    # ClientError: An error occurred (InvalidParameterValueException) when
    # calling the CreateFunction operation: The role defined for the function
    # cannot be assumed by Lambda.
    # current assumption is that the role is not propagated to lambda in time
    time.sleep(15)

    return role


def _precond_check():
    """Make sure the default AWS profile is set so the test can run on AWS."""
    if not os.getenv('USER', None).endswith('jenkins') and \
            not os.getenv('AWS_DEFAULT_PROFILE', None):
        print("AWS_DEFAULT_PROFILE variable not set! Test is skipped.")
        return True
    if not os.getenv('ENV', None):
        print("ENV environment variable not set! Test is skipped.")
        return True
    if not os.getenv('ACCOUNT', None):
        print("ACCOUNT environment variable not set! Test is skipped.")
        return True

    return False


# skipif helper check_preconditions
check_preconditions = pytest.mark.skipif(
    _precond_check(),
    reason="Set environment variables to run tests on AWS (see gcdt docs)."
)


def is_playback_mode():
    """Make sure the placebo mode is 'playback'."""
    if os.getenv('PLACEBO_MODE', '').lower() in ['record', 'normal']:
        return False
    else:
        return True


# skipif helper aswclient_placebo mode
# not this needs to invert the check
check_playback_mode = pytest.mark.skipif(
    not is_playback_mode(),
    reason="Test runs only in playback mode (not normal or record)."
)


def is_normal_mode():
    """Make sure the placebo mode is 'playback'."""
    if os.getenv('PLACEBO_MODE', '').lower() == 'normal':
        return True
    else:
        return False


# skipif helper aswclient_placebo mode
# not this needs to invert the check
check_normal_mode = pytest.mark.skipif(
    not is_normal_mode(),
    reason="Test runs only in normal mode (not record or playback)."
)


@pytest.fixture(scope='function')  # 'function' or 'module'
def awsclient(request):
    def there(p):
        # waited a long time to find a problem where I can use this ;)
        return os.path.abspath(os.path.join(
            os.path.dirname(request.module.__file__), p))

    random_string_orig = utils.random_string
    time_now_orig = utils.time_now
    sleep_orig = time.sleep
    random_string_filename = 'random_string.txt'
    time_now_filename = 'time_now.txt'
    prefix = request.module.__name__ + '.' + request.function.__name__
    record_dir = os.path.join(there('./resources/placebo_awsclient'), prefix)

    client = PlaceboAWSClient(botocore.session.Session(), data_path=record_dir)
    if os.getenv('PLACEBO_MODE', '').lower() == 'record':
        if not os.path.exists(record_dir):
            os.makedirs(record_dir)
        client.record()
        utils.random_string = recorder(record_dir, random_string_orig,
                                            filename=random_string_filename)
        utils.time_now = recorder(record_dir, time_now_orig,
                                       filename=time_now_filename)
    elif os.getenv('PLACEBO_MODE', '').lower() == 'normal':
        # neither record nor playback, just run the tests against AWS services
        pass
    else:
        if not os.path.exists(record_dir):
            raise Exception('placebo playback for \'%s\' missing' % prefix)
        def fake_sleep(seconds):
            pass

        #utils.random_string = file_reader(record_dir,
        #                                  random_string_filename)
        # implementing a wrapper for length validation
        _file_reader = file_reader(record_dir, random_string_filename)
        def _random_string(length=6):
            s = _file_reader()
            assert len(s) == length
            print(s)
            return s
        utils.random_string = _random_string
        utils.time_now = file_reader(record_dir, time_now_filename, 'int')
        time.sleep = fake_sleep
        client.playback()

    yield client

    # cleanup
    client.stop()
    # restore original functionality
    utils.random_string = random_string_orig
    helpers.recordable_now = time_now_orig
    time.sleep = sleep_orig


# TODO use recorder for datetime.now() calls!!

def recorder(record_dir, function, filename=None):
    """this helper wraps a function and writes results to a file
    default filename is the name of the function.

    :param record_dir: where to write the file
    :param function: function to wrap
    :return: wrapped function
    """
    if not filename:
        filename = function.__name__
    if not os.path.exists(record_dir):
        os.makedirs(record_dir)

    def wrapper():
        with open(os.path.join(record_dir, filename), 'a') as rfile:
            result = function()
            print(str(result), file=rfile)
            return result

    return wrapper


def file_reader(record_dir, filename, datatype=None):
    """helper to read a file line by line
    basically same as dfile.next but strips whitespace

    :param record_dir:
    :param filename:
    :return: function that returns a line when called
    """
    path = os.path.join(record_dir, filename)
    if os.path.isfile(path):
        with open(path, 'r') as dfile:
            data = [line.strip() for line in dfile]
            idata = iter(data)

            def f():
                line = next(idata).strip()
                if datatype and datatype == 'int':
                    return int(line)
                return line
    else:
        # if file does not exist
        def f():
            return ''

    return f


def get_tooldata(awsclient, tool, command, config=None, config_base_name=None,
                 location=None):
    """Helper for main tests to assemble tool data.
    used in testing to read from 'gcdt_<env>.json' files

    :param awsclient:
    :param tool:
    :param command:
    :param config: provide custom config or empty to read from file
    :param config_base_name:
    :param location:
    :return:
    """
    from gcdt_lookups.lookups import _resolve_lookups
    if config is None:
        if config_base_name is None:
            config_base_name = 'gcdt'
        if location is None:
            location = '.'
        env = get_env()
        gcdt_config_file = os.path.join(location,
                                        '%s_%s.json' % (config_base_name, env))
        context = {'_awsclient': awsclient, 'tool': tool, 'command': command}
        config = fix_old_kumo_config(read_json_config(gcdt_config_file))[tool]
        _resolve_lookups(context, config, config.get('lookups',
                                                     ['secret', 'ssl', 'stack',
                                                      'baseami']))

    tooldata = {
        'context': {
            'tool': tool,
            'command': command,
            'version': __version__,
            'user': 'unittest',
            '_awsclient': awsclient
        },
        'config': config
    }
    return tooldata


@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_roles(awsclient):
    items = []
    yield items
    # cleanup
    for i in items:
        delete_role_helper(awsclient, i)


@pytest.fixture(scope='function')  # 'function' or 'module'
def temp_cloudformation_policy(awsclient):
    # policy: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-template.html
    '''
    {
        "Version":"2012-10-17",
        "Statement":[{
            "Effect":"Allow",
            "Action":[
                "cloudformation:CreateStack",
                "cloudformation:DescribeStacks",
                "cloudformation:DescribeStackEvents",
                "cloudformation:DescribeStackResources",
                "cloudformation:GetTemplate",
                "cloudformation:ValidateTemplate"
            ],
            "Resource":"*"
        }]
    }
    '''
    client_iam = awsclient.get_client('iam')
    name = 'unittest_%s_cloudformation_policy' % utils.random_string()
    pd = Policy(
        Version="2012-10-17",
        Id=name,
        Statement=[
            Statement(
                Effect=Allow,
                Action=[Action('cloudformation', '*')],
                Resource=['*']
            ),
        ],
    )

    response = client_iam.create_policy(
        PolicyName=name,
        PolicyDocument=pd.to_json()
    )

    yield response['Policy']['Arn']

    # cleanup
    client_iam.delete_policy(PolicyArn=response['Policy']['Arn'])
