# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from funcsigs import signature  # python3 only: from inspect import signature
import imp
import json
import random
import string
import sys
import time
import logging

import os
import six
from clint.textui import colored, prompt
from tabulate import tabulate

from .utils import get_env
from .s3 import upload_file_to_s3
from .gcdt_signals import check_hook_mechanism_is_intact, \
    check_register_present

log = logging.getLogger(__name__)


def load_cloudformation_template(path=None):
    """Load cloudformation template from path.

    :param path: Absolute or relative path of cloudformation template. Defaults to cwd.
    :return: module, success
    """
    if not path:
        path = os.path.abspath('cloudformation.py')
    else:
        path = os.path.abspath(path)
    if isinstance(path, six.string_types):
        try:
            sp = sys.path
            # temporarily add folder to allow relative path
            sys.path.append(os.path.abspath(os.path.dirname(path)))
            cloudformation = imp.load_source('cloudformation', path)
            sys.path = sp  # restore
            # use cfn template hooks
            if not check_hook_mechanism_is_intact(cloudformation):
                # no hooks - do nothing
                log.debug('No valid hook configuration: \'%s\'. Not using hooks!', path)
            else:
                if check_register_present(cloudformation):
                    # register the template hooks so they listen to gcdt_signals
                    cloudformation.register()
            return cloudformation, True
        except ImportError as e:
            print('could not find package for import: %s' % e)
        except Exception as e:
            print('could not import cloudformation.py, maybe something wrong ',
                  'with your code?')
            print(e)
    return None, False


def get_parameter_diff(awsclient, config):
    """get differences between local config and currently active config
    """
    client_cf = awsclient.get_client('cloudformation')
    try:
        stackname = config['cloudformation']['StackName']
        if stackname:
            response = client_cf.describe_stacks(StackName=stackname)
            if response['Stacks']:
                stack_id = response['Stacks'][0]['StackId']
                stack = response['Stacks'][0]
            else:
                return None
        else:
            print('StackName is not configured, could not create parameter diff')
            return None
    except:
        # probably the stack is not existent
        return None

    changed = 0
    table = []
    table.append(['Parameter', 'Current Value', 'New Value'])

    # Check if there are parameters for the stack
    if 'Parameters' in stack:
        for param in stack['Parameters']:
            try:
                old = str(param['ParameterValue'])
                # can not compare list with str!!
                #if ',' in old:
                #    old = old.split(',')
                new = config['cloudformation'][param['ParameterKey']]
                if old != new:
                    if old.startswith('***'):
                        # parameter is configured with `NoEcho=True`
                        # this means we can not really say if the value changed!!
                        # for security reasons we block viewing the new value
                        new = old
                    table.append([param['ParameterKey'], old, new])
                    changed += 1
            except Exception:
                print('Did not find %s in local config file' % param['ParameterKey'])

    if changed > 0:
        print(tabulate(table, tablefmt='fancy_grid'))

    return changed > 0


def call_pre_hook(awsclient, cloudformation):
    """Invoke the pre_hook BEFORE the config is read.

    :param awsclient:
    :param cloudformation:
    """
    # TODO: this is deprecated!! move this to glomex_config_reader
    # no config available
    if not hasattr(cloudformation, 'pre_hook'):
        # hook is not present
        return
    hook_func = getattr(cloudformation, 'pre_hook')
    if not hook_func.func_code.co_argcount:
        hook_func()  # for compatibility with existing templates
    else:
        log.error('pre_hock can not have any arguments. The pre_hook it is ' +
                  'executed BEFORE config is read')


def _call_hook(awsclient, config, stack_name, parameters, cloudformation,
               hook, message=None):
    # TODO: this is deprecated!! move this to glomex_config_reader
    if hook not in ['pre_hook', 'pre_create_hook', 'pre_update_hook',
                    'post_create_hook', 'post_update_hook', 'post_hook']:
        print(colored.green('Unknown hook: %s' % hook))
        return
    if not hasattr(cloudformation, hook):
        # hook is not present
        return
    if not message:
        message = 'Executing %s...' % hook.replace('_', ' ')
    print(colored.green(message))
    hook_func = getattr(cloudformation, hook)
    sig = signature(hook_func)
    params = sig.parameters

    #if not hook_func.func_code.co_argcount:
    if len(params) == 0:
        hook_func()  # for compatibility with existing templates
    else:
        # new call for templates with parametrized hooks
        client_cf = awsclient.get_client('cloudformation')
        stack_outputs = _get_stack_outputs(client_cf, stack_name)
        stack_state = _get_stack_state(client_cf, stack_name)
        hook_func(awsclient=awsclient, config=config,
                  parameters=parameters, stack_outputs=stack_outputs,
                  stack_state=stack_state)


# TODO research CloudFormation Exports
def _get_stack_outputs(cfn_client, stack_name):
    response = cfn_client.describe_stacks(StackName=stack_name)
    if response['Stacks']:
        stack = response['Stacks'][0]
        if 'Outputs' in stack:
            return stack['Outputs']


def _get_stack_state(client_cf, stackname):
    try:
        response = client_cf.describe_stacks(StackName=stackname)
        if response['Stacks']:
            stack = response['Stacks'][0]
            return stack['StackStatus']
    except:
        print('Failed to get stack state.')
        return


def _json2table(data):
    filter_terms = ['ResponseMetadata']
    table = []
    try:
        for k, v in filter(lambda k, v: k not in filter_terms, data.iteritems()):
            table.append([k, str(v)])
        return tabulate(table, tablefmt='fancy_grid')
    except Exception:
        return data


def _get_stack_id(awsclient, stackname):
    client = awsclient.get_client('cloudformation')
    response = client.describe_stacks(StackName=stackname)
    stack_id = response['Stacks'][0]['StackId']
    return stack_id


def _get_stack_events_last_timestamp(awsclient, stackname):
    # we need to get the last event since updatedTime is when the update stated
    client = awsclient.get_client('cloudformation')
    stack_id = _get_stack_id(awsclient, stackname)
    response = client.describe_stack_events(StackName=stack_id)
    return response['StackEvents'][-1]['Timestamp']


def _poll_stack_events(awsclient, stackname, last_event=None):
    # http://stackoverflow.com/questions/796008/cant-subtract-offset-naive-and-offset-aware-datetimes/25662061#25662061
    finished_statuses = ['CREATE_COMPLETE',
                         'CREATE_FAILED',
                         'DELETE_COMPLETE',
                         'DELETE_FAILED',
                         'ROLLBACK_COMPLETE',
                         'ROLLBACK_FAILED',
                         'UPDATE_COMPLETE',
                         'UPDATE_ROLLBACK_COMPLETE',
                         'UPDATE_ROLLBACK_FAILED']

    failed_statuses = ['CREATE_FAILED',
                       'DELETE_FAILED',
                       'ROLLBACK_COMPLETE',
                       'ROLLBACK_FAILED',
                       'UPDATE_ROLLBACK_COMPLETE',
                       'UPDATE_ROLLBACK_FAILED']

    warning_statuses = ['ROLLBACK_IN_PROGRESS',
                        'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
                        'UPDATE_ROLLBACK_IN_PROGRESS']

    success_statuses = ['CREATE_COMPLETE',
                        'DELETE_COMPLETE',
                        'UPDATE_COMPLETE']

    seen_events = []
    # print len(seen_events)
    client = awsclient.get_client('cloudformation')
    status = ''
    # for the delete command we need the stack_id
    stack_id = _get_stack_id(awsclient, stackname)
    print('%-50s %-25s %-50s %-25s\n' % ('Resource Status', 'Resource ID',
                                         'Reason', 'Timestamp'))
    while status not in finished_statuses:
        response = client.describe_stack_events(StackName=stack_id)
        for event in response['StackEvents'][::-1]:
            if event['EventId'] not in seen_events and \
                    (not last_event or event['Timestamp'] > last_event):
                seen_events.append(event['EventId'])
                resource_status = event['ResourceStatus']
                resource_id = event['LogicalResourceId']
                # this is not always present
                try:
                    reason = event['ResourceStatusReason']
                except KeyError:
                    reason = ''
                timestamp = str(event['Timestamp'])
                message = '%-50s %-25s %-50s %-25s\n' % (resource_status, resource_id,
                                                         reason, timestamp)
                if resource_status in failed_statuses:
                    print(colored.red(message))
                elif resource_status in warning_statuses:
                    print(colored.yellow(message))
                elif resource_status in success_statuses:
                    print(colored.green(message))
                else:
                    print(message)
                if event['LogicalResourceId'] == stackname:
                    status = event['ResourceStatus']
        time.sleep(5)
    exit_code = 0
    if status not in success_statuses:
        exit_code = 1
    return exit_code


def _generate_parameter_entry(conf, raw_param):
    # generate an entry for the parameter list from a raw value read from config
    entry = {
        'ParameterKey': raw_param,
        'ParameterValue': _get_conf_value(conf, raw_param),
        'UsePreviousValue': False
    }
    return entry


def _get_conf_value(conf, raw_param):
    conf_value = conf['cloudformation'][raw_param]
    if isinstance(conf_value, list):
        # if list or array then join to comma separated list
        return ','.join(conf_value)
    else:
        return conf_value


def _generate_parameters(conf):
    # generate the parameter list for the cloudformation template from the
    # conf keys
    raw_parameters = []
    parameter_list = []
    # this looks weird since it should work only on the 'cloudformation' config
    #for item in conf.iterkeys():
    #    for key in conf[item].iterkeys():
    #for key in conf['cloudformation'].iterkeys():
    for key in conf['cloudformation'].keys():
        if key not in ['StackName', 'TemplateBody', 'ArtifactBucket']:
            raw_parameters.append(key)
    for param in raw_parameters:
        entry = _generate_parameter_entry(conf, param)
        parameter_list.append(entry)

    return parameter_list


def stack_exists(awsclient, stackName):
    # TODO handle failure based on API call limit
    client = awsclient.get_client('cloudformation')
    try:
        response = client.describe_stacks(
            StackName=stackName
        )
    except Exception:
        return False
    else:
        return True


def deploy_stack(awsclient, conf, cloudformation, override_stack_policy=False):
    """Deploy the stack to AWS cloud. Does either create or update the stack.

    :param conf:
    :param override_stack_policy:
    :return: exit_code
    """
    stackname = _get_stack_name(conf)
    parameters = _generate_parameters(conf)
    if stack_exists(awsclient, stackname):
        exit_code = _update_stack(awsclient, conf, cloudformation,
                                  parameters, override_stack_policy)
    else:
        exit_code = _create_stack(awsclient, conf, cloudformation,
                                  parameters)
    _call_hook(awsclient, conf, stackname, parameters, cloudformation,
               hook='post_hook',
               message='CloudFormation is done, now executing post hook...')
    return exit_code


def _get_stack_policy(cloudformation):
    default_stack_policy = json.dumps({
        'Statement': [
            {
                'Effect': 'Allow',
                'Action': 'Update:Modify',
                'Principal': '*',
                'Resource': '*'
            },
            {
                'Effect': 'Deny',
                'Action': ['Update:Replace', 'Update:Delete'],
                'Principal': '*',
                'Resource': '*'
            }
        ]
    })

    stack_policy = default_stack_policy

    # check if a user specified his own stack policy
    # if CLOUDFORMATION_FOUND:
    if 'get_stack_policy' in dir(cloudformation):
        stack_policy = cloudformation.get_stack_policy()
        print(colored.magenta('Applying custom stack policy'))

    return stack_policy


def _get_stack_policy_during_update(cloudformation, override_stack_policy):
    if override_stack_policy:
        default_stack_policy_during_update = json.dumps({
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 'Update:*',
                    'Principal': '*',
                    'Resource': '*'
                }
            ]
        })
    else:
        default_stack_policy_during_update = json.dumps({
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 'Update:Modify',
                    'Principal': '*',
                    'Resource': '*'
                },
                {
                    'Effect': 'Deny',
                    'Action': ['Update:Replace', 'Update:Delete'],
                    'Principal': '*',
                    'Resource': '*'
                }
            ]
        })

    stack_policy_during_update = default_stack_policy_during_update

    # check if a user specified his own stack policy
    # if CLOUDFORMATION_FOUND:
    if 'get_stack_policy_during_update' in dir(cloudformation):
        stack_policy_during_update = cloudformation.get_stack_policy_during_update()
        print(colored.magenta('Applying custom stack policy for updates\n'))

    return stack_policy_during_update


def _create_stack(awsclient, conf, cloudformation, parameters):
    # create stack with all the information we have
    client_cf = awsclient.get_client('cloudformation')
    stackname = _get_stack_name(conf)
    _call_hook(awsclient, conf, stackname, parameters, cloudformation,
               hook='pre_create_hook')
    if _get_artifact_bucket(conf):
        response = client_cf.create_stack(
            StackName=_get_stack_name(conf),
            TemplateURL=_s3_upload(awsclient, conf, cloudformation),
            Parameters=parameters,
            Capabilities=[
                'CAPABILITY_IAM',
            ],
            StackPolicyBody=_get_stack_policy(cloudformation),
        )
    else:
        # if we have no artifacts bucket configured then upload the template directly
        response = client_cf.create_stack(
            StackName=_get_stack_name(conf),
            TemplateBody=cloudformation.generate_template(),
            Parameters=parameters,
            Capabilities=[
                'CAPABILITY_IAM',
            ],
            StackPolicyBody=_get_stack_policy(cloudformation),
        )

    exit_code = _poll_stack_events(awsclient, stackname)
    _call_hook(awsclient, conf, stackname, parameters, cloudformation,
               hook='post_create_hook',
               message='CloudFormation is done, now executing post create hook...')
    return exit_code


def _s3_upload(awsclient, conf, cloudformation):
    region = awsclient.get_client('s3').meta.region_name
    bucket = _get_artifact_bucket(conf)
    dest_key = 'kumo/%s/%s-cloudformation.json' % (region, _get_stack_name(conf))
    source_file = generate_template_file(conf, cloudformation)
    upload_file_to_s3(awsclient, bucket, dest_key, source_file)
    s3url = 'https://s3-%s.amazonaws.com/%s/%s' % (region, bucket, dest_key)
    return s3url


def _update_stack(awsclient, conf, cloudformation, parameters,
                  override_stack_policy):
    # update stack with all the information we have
    exit_code = 0
    client_cf = awsclient.get_client('cloudformation')
    stackname = _get_stack_name(conf)
    last_event = _get_stack_events_last_timestamp(awsclient, stackname)
    try:
        _call_hook(awsclient, conf, stackname, parameters, cloudformation,
                   hook='pre_update_hook')
        #try:
        if _get_artifact_bucket(conf):
            response = client_cf.update_stack(
                StackName=_get_stack_name(conf),
                TemplateURL=_s3_upload(awsclient, conf, cloudformation),
                Parameters=parameters,
                Capabilities=[
                    'CAPABILITY_IAM',
                ],
                StackPolicyBody=_get_stack_policy(cloudformation),
                StackPolicyDuringUpdateBody=_get_stack_policy_during_update(
                    cloudformation,
                    override_stack_policy)

            )
        else:
            # if we have no artifacts bucket configured then upload the template directly
            #except ConfigMissingException:
            response = client_cf.update_stack(
                StackName=_get_stack_name(conf),
                TemplateBody=cloudformation.generate_template(),
                Parameters=parameters,
                Capabilities=[
                    'CAPABILITY_IAM',
                ],
                StackPolicyBody=_get_stack_policy(cloudformation),
                StackPolicyDuringUpdateBody=_get_stack_policy_during_update(
                    cloudformation,
                    override_stack_policy)
            )

        exit_code = _poll_stack_events(awsclient, stackname, last_event)
        _call_hook(awsclient, conf, stackname, parameters, cloudformation,
                   hook='post_update_hook',
                   message='CloudFormation is done, now executing post update hook...')
    except Exception as e:
        if 'No updates' in repr(e):
            print(colored.yellow('No updates are to be performed.'))
        else:
            print(type(e))
            print(colored.red('Exception occurred during update: ' + str(e)))

    return exit_code


def delete_stack(awsclient, conf):
    """Delete the stack from AWS cloud.

    :param awsclient:
    :param conf:
    """
    client_cf = awsclient.get_client('cloudformation')
    stackname = _get_stack_name(conf)
    last_event = _get_stack_events_last_timestamp(awsclient, stackname)
    response = client_cf.delete_stack(
        StackName=_get_stack_name(conf),
    )
    return _poll_stack_events(awsclient, stackname, last_event)


def list_stacks(awsclient):
    """Print out the list of stacks deployed at AWS cloud.

    :param awsclient:
    :return:
    """
    client_cf = awsclient.get_client('cloudformation')
    response = client_cf.list_stacks(
        StackStatusFilter=[
            'CREATE_IN_PROGRESS', 'CREATE_COMPLETE', 'ROLLBACK_IN_PROGRESS',
            'ROLLBACK_COMPLETE', 'DELETE_IN_PROGRESS', 'DELETE_FAILED',
            'UPDATE_IN_PROGRESS', 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
            'UPDATE_COMPLETE', 'UPDATE_ROLLBACK_IN_PROGRESS',
            'UPDATE_ROLLBACK_FAILED', 'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
            'UPDATE_ROLLBACK_COMPLETE',
        ]
    )
    result = {}
    stack_sum = 0
    for summary in response['StackSummaries']:
        result['StackName'] = summary["StackName"]
        result['CreationTime'] = summary['CreationTime']
        result['StackStatus'] = summary['StackStatus']
        print(_json2table(result))
        stack_sum += 1
    print('listed %s stacks' % str(stack_sum))


def create_change_set(awsclient, conf, cloudformation):
    client = awsclient.get_client('cloudformation')
    change_set_name = ''.join(random.SystemRandom().choice(
        string.ascii_uppercase) for _ in range(8))
    response = client.create_change_set(
        StackName=_get_stack_name(conf),
        TemplateBody=cloudformation.generate_template(),
        Parameters=_generate_parameters(conf),
        Capabilities=[
            'CAPABILITY_IAM',
        ],
        ChangeSetName=change_set_name
    )
    # print json2table(response)
    # TODO catch nonexistant stack (ValidationError)
    return change_set_name, _get_stack_name(conf)


def describe_change_set(awsclient, change_set_name, stack_name):
    """Print out the change_set to console.
    This needs to run create_change_set first.

    :param awsclient:
    :param change_set_name:
    :param stack_name:
    """
    client = awsclient.get_client('cloudformation')

    status = None
    while status not in ['CREATE_COMPLETE', 'FAILED']:
        response = client.describe_change_set(
            ChangeSetName=change_set_name,
            StackName=stack_name)
        status = response['Status']
        #print('##### %s' % status)
        if status == 'CREATE_COMPLETE':
            for change in response['Changes']:
                print(_json2table(change['ResourceChange']))


def _get_stack_name(conf):
    return conf['cloudformation']['StackName']


def _get_artifact_bucket(conf):
    bucket = conf['cloudformation'].get('artifactBucket')
    if bucket:
        return bucket


def generate_template_file(conf, cloudformation):
    """Writes the template to disk
    """
    template_body = cloudformation.generate_template()
    template_file_name = _get_stack_name(conf) + '-generated-cf-template.json'
    with open(template_file_name, 'w') as opened_file:
        opened_file.write(template_body)
    print('wrote cf-template for %s to disk: %s' % (get_env(), template_file_name))
    return template_file_name
