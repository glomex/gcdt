# -*- coding: utf-8 -*-

"""ramuda.
Script to deploy Lambda functions to AWS
"""

from __future__ import unicode_literals, print_function
import sys
import os
import shutil
import uuid
import time
#from datetime import datetime, timedelta
import json
import logging

from botocore.exceptions import ClientError as ClientError
from clint.textui import colored
import maya

from gcdt.ramuda_utils import json2table, s3_upload, \
    lambda_exists, create_sha256, get_remote_code_hash, unit, \
    aggregate_datapoints, list_of_dict_equals, \
    create_aws_s3_arn, get_bucket_from_s3_arn, get_rule_name_from_event_arn, \
    build_filter_rules


log = logging.getLogger(__name__)
ALIAS_NAME = 'ACTIVE'
ENSURE_OPTIONS = ['absent', 'exists']


def _create_alias(awsclient, function_name, function_version,
                  alias_name=ALIAS_NAME):
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.create_alias(
        FunctionName=function_name,
        Name=alias_name,
        FunctionVersion=function_version,

    )
    return response['AliasArn']


def _update_alias(awsclient, function_name, function_version,
                  alias_name=ALIAS_NAME):
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.update_alias(
        FunctionName=function_name,
        Name=alias_name,
        FunctionVersion=function_version,

    )
    return response['AliasArn']


def _alias_exists(awsclient, function_name, alias_name):
    client_lambda = awsclient.get_client('lambda')
    try:
        client_lambda.get_alias(
            FunctionName=function_name,
            Name=alias_name
        )
        return True
    except Exception:
        return False


def _get_alias_version(awsclient, function_name, alias_name):
    # this is used for testing - it returns the version
    client_lambda = awsclient.get_client('lambda')
    try:
        response = client_lambda.get_alias(
            FunctionName=function_name,
            Name=alias_name
        )
        return response['FunctionVersion']
    except Exception:
        return


def _get_version_from_response(data):
    version = data['Version']
    return int(version) if version.isdigit() else 0


def _get_previous_version(awsclient, function_name, alias_name):
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.get_alias(
        FunctionName=function_name,
        Name=alias_name
    )
    current_version = response['FunctionVersion']
    if current_version != '$LATEST':
        return str(int(current_version) - 1)

    max_version = 0
    marker = None
    request_more_versions = True
    while request_more_versions:
        kwargs = {'Marker': marker} if marker else {}
        response = client_lambda.list_versions_by_function(
            FunctionName=function_name, **kwargs)
        if 'Marker' not in response:
            request_more_versions = False
        else:
            marker = response['Marker']
        versions = list(map(_get_version_from_response, response['Versions']))
        versions.append(max_version)
        max_version = max(versions)
    return str(max(0, max_version - 1))


def _deploy_alias(awsclient, function_name, function_version,
                  alias_name=ALIAS_NAME):
    if _alias_exists(awsclient, function_name, alias_name):
        _update_alias(awsclient, function_name, function_version, alias_name)
    else:
        _create_alias(awsclient, function_name, function_version, alias_name)


def _lambda_add_time_schedule_event_source(awsclient, rule_name,
                                           rule_description,
                                           schedule_expression, lambda_arn):
    client_event = awsclient.get_client('events')
    client_event.put_rule(
        Name=rule_name,
        ScheduleExpression=schedule_expression,
        Description=rule_description,
    )
    rule_response = client_event.describe_rule(Name=rule_name)
    if rule_response is not None:
        client_event.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': lambda_arn,
                },
            ]
        )

    return rule_response['Arn']


def _lambda_add_invoke_permission(awsclient, function_name,
                                  source_principal,
                                  source_arn, alias_name=ALIAS_NAME):
    # https://www.getoto.net/noise/2015/08/20/better-together-amazon-ecs-and-aws-lambda/
    # http://docs.aws.amazon.com/cli/latest/reference/lambda/add-permission.html
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.add_permission(
        FunctionName=function_name,
        StatementId=str(uuid.uuid1()),
        Action='lambda:InvokeFunction',
        Principal=source_principal,
        SourceArn=source_arn,
        Qualifier=alias_name
    )
    return response


def _lambda_add_s3_event_source(awsclient, arn, event, bucket, prefix,
                                suffix):
    """Use only prefix OR suffix

    :param arn:
    :param event:
    :param bucket:
    :param prefix:
    :param suffix:
    :return:
    """
    json_data = {
        'LambdaFunctionConfigurations': [{
            'LambdaFunctionArn': arn,
            'Id': str(uuid.uuid1()),
            'Events': [event]
        }]
    }

    filter_rules = build_filter_rules(prefix, suffix)

    json_data['LambdaFunctionConfigurations'][0].update({
        'Filter': {
            'Key': {
                'FilterRules': filter_rules
            }
        }
    })
    # http://docs.aws.amazon.com/cli/latest/reference/s3api/put-bucket-notification-configuration.html
    # http://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html
    client_s3 = awsclient.get_client('s3')

    bucket_configurations = client_s3.get_bucket_notification_configuration(
        Bucket=bucket)
    bucket_configurations.pop('ResponseMetadata')

    if 'LambdaFunctionConfigurations' in bucket_configurations:
        bucket_configurations['LambdaFunctionConfigurations'].append(
            json_data['LambdaFunctionConfigurations'][0]
        )
    else:
        bucket_configurations['LambdaFunctionConfigurations'] = json_data[
            'LambdaFunctionConfigurations']

    response = client_s3.put_bucket_notification_configuration(
        Bucket=bucket,
        NotificationConfiguration=bucket_configurations
    )
    # TODO don't return a table, but success state
    return json2table(response)


def list_functions(awsclient):
    """List the deployed lambda functions and print configuration.

    :return: exit_code
    """
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.list_functions()
    for function in response['Functions']:
        print(function['FunctionName'])
        print('\t' 'Memory: ' + str(function['MemorySize']))
        print('\t' 'Timeout: ' + str(function['Timeout']))
        print('\t' 'Role: ' + str(function['Role']))
        print('\t' 'Current Version: ' + str(function['Version']))
        print('\t' 'Last Modified: ' + str(function['LastModified']))
        print('\t' 'CodeSha256: ' + str(function['CodeSha256']))

        print('\n')
    return 0


def deploy_lambda(awsclient, function_name, role, handler_filename,
                  handler_function,
                  folders, description, timeout, memory, subnet_ids=None,
                  security_groups=None, artifact_bucket=None,
                  zipfile=None,
                  fail_deployment_on_unsuccessful_ping=False,
                  runtime='python2.7', settings=None):
    """Create or update a lambda function.

    :param awsclient:
    :param function_name:
    :param role:
    :param handler_filename:
    :param handler_function:
    :param folders:
    :param description:
    :param timeout:
    :param memory:
    :param subnet_ids:
    :param security_groups:
    :param artifact_bucket:
    :param zipfile:
    :return: exit_code
    """
    if lambda_exists(awsclient, function_name):
        function_version = _update_lambda(awsclient, function_name,
                                          handler_filename,
                                          handler_function, folders, role,
                                          description, timeout, memory,
                                          subnet_ids, security_groups,
                                          artifact_bucket=artifact_bucket,
                                          zipfile=zipfile
                                        )
    else:
        if not zipfile:
            return 1
        log.info('buffer size: %0.2f MB' % float(len(zipfile) / 1000000.0))
        function_version = _create_lambda(awsclient, function_name, role,
                                          handler_filename, handler_function,
                                          folders, description, timeout,
                                          memory, subnet_ids, security_groups,
                                          artifact_bucket, zipfile,
                                          runtime=runtime)
    pong = ping(awsclient, function_name, version=function_version)
    if 'alive' in str(pong):
        print(colored.green('Great you\'re already accepting a ping ' +
                            'in your Lambda function'))
    elif fail_deployment_on_unsuccessful_ping and not 'alive' in pong:
        print(colored.red('Pinging your lambda function failed'))
        # we do not deploy alias and fail command
        return 1
    else:
        print(colored.red('Please consider adding a reaction to a ' +
                          'ping event to your lambda function'))
    _deploy_alias(awsclient, function_name, function_version)
    return 0


def _create_lambda(awsclient, function_name, role, handler_filename,
                   handler_function,
                   folders, description, timeout, memory,
                   subnet_ids=None, security_groups=None,
                   artifact_bucket=None, zipfile=None, runtime='python2.7'):
    log.debug('create lambda function: %s' % function_name)
    # move to caller!
    # _install_dependencies_with_pip('requirements.txt', './vendored')
    client_lambda = awsclient.get_client('lambda')
    # print ('creating function %s with role %s handler %s folders %s timeout %s memory %s') % (
    # function_name, role, handler_filename, str(folders), str(timeout), str(memory))

    if not artifact_bucket:
        log.debug('create without artifact bucket...')
        response = client_lambda.create_function(
            FunctionName=function_name,
            Runtime=runtime,
            Role=role,
            Handler=handler_function,
            Code={
                'ZipFile': zipfile
            },
            Description=description,
            Timeout=int(timeout),
            MemorySize=int(memory),
            Publish=True
        )
    elif artifact_bucket and zipfile:
        log.debug('create with artifact bucket...')
        # print 'uploading bundle to s3'
        log.debug('uploading artifact...')
        dest_key, e_tag, version_id = \
            s3_upload(awsclient, artifact_bucket, zipfile, function_name)
        log.debug('call create_function')
        # print dest_key, e_tag, version_id
        response = client_lambda.create_function(
            FunctionName=function_name,
            Runtime=runtime,
            Role=role,
            Handler=handler_function,
            Code={
                'S3Bucket': artifact_bucket,
                'S3Key': dest_key,
                'S3ObjectVersion': version_id
            },
            Description=description,
            Timeout=int(timeout),
            MemorySize=int(memory),
            Publish=True
        )
    else:
        log.debug('no zipfile and no artifact_bucket -> nothing to do!')
        # no zipfile and no artifact_bucket -> nothing to do!
        return
    log.debug('lambda create completed...')

    function_version = response['Version']
    print(json2table(response))
    # FIXME: 23.08.2016 WHY update configuration after create?
    # timing issue:
    # http://jenkins.dev.dp.glomex.cloud/job/packages/job/gcdt_pull_request/32/console
    #       1) we need to wait till the function is available for update
    #          is there a better way than sleep?
    time.sleep(15)
    #       2) I believe this was implemented as shortcut to set subnet, and sg
    #          a way better way is to set this is using the using VPCConfig argument!
    _update_lambda_configuration(
        awsclient, function_name, role, handler_function, description,
        timeout, memory, subnet_ids, security_groups
    )
    return function_version


def _update_lambda(awsclient, function_name, handler_filename,
                   handler_function, folders,
                   role, description, timeout, memory, subnet_ids=None,
                   security_groups=None, artifact_bucket=None,
                   zipfile=None
                   ):
    log.debug('update lambda function: %s', function_name)
    _update_lambda_function_code(awsclient, function_name,
                                 artifact_bucket=artifact_bucket,
                                 zipfile=zipfile
    )
    function_version = \
        _update_lambda_configuration(
            awsclient, function_name, role, handler_function,
            description, timeout, memory, subnet_ids, security_groups
        )
    return function_version


def bundle_lambda(zipfile):
    """Write zipfile contents to file.

    :param zipfile:
    :return: exit_code
    """
    # TODO have 'bundle.zip' as default config
    if not zipfile:
        return 1
    with open('bundle.zip', 'wb') as zfile:
        zfile.write(zipfile)
    print('Finished - a bundle.zip is waiting for you...')
    return 0


def _update_lambda_function_code(
        awsclient, function_name,
        artifact_bucket=None,
        zipfile=None
        ):
    client_lambda = awsclient.get_client('lambda')
    if not zipfile:
        return 1
    local_hash = create_sha256(zipfile)
    # print ('getting remote hash')

    # print local_hash
    remote_hash = get_remote_code_hash(awsclient, function_name)
    # print remote_hash
    if local_hash == remote_hash:
        print('Code hasn\'t changed - won\'t upload code bundle')
    else:
        if not artifact_bucket:
            log.info('no stack bucket found')
            response = client_lambda.update_function_code(
                FunctionName=function_name,
                ZipFile=zipfile,
                Publish=True
            )
        else:
            # reuse the zipfile we already created!
            dest_key, e_tag, version_id = \
                s3_upload(awsclient, artifact_bucket, zipfile, function_name)
            # print dest_key, e_tag, version_id
            response = client_lambda.update_function_code(
                FunctionName=function_name,
                S3Bucket=artifact_bucket,
                S3Key=dest_key,
                S3ObjectVersion=version_id,
                Publish=True
            )
        print(json2table(response))
    return 0


def _update_lambda_configuration(awsclient, function_name, role,
                                 handler_function,
                                 description, timeout, memory, subnet_ids=None,
                                 security_groups=None):
    log.debug('update lambda configuration for function: %s' % function_name)
    client_lambda = awsclient.get_client('lambda')
    if subnet_ids and security_groups:
        # print ('found vpc config')
        response = client_lambda.update_function_configuration(
            FunctionName=function_name,
            Role=role,
            Handler=handler_function,
            Description=description,
            Timeout=timeout,
            MemorySize=memory,
            VpcConfig={
                'SubnetIds': subnet_ids,
                'SecurityGroupIds': security_groups
            }
        )
        print(json2table(response))
    else:
        response = client_lambda.update_function_configuration(
            FunctionName=function_name,
            Role=role,
            Handler=handler_function,
            Description=description,
            Timeout=timeout,
            MemorySize=memory)

        print(json2table(response))
    function_version = response['Version']
    return function_version


def get_metrics(awsclient, name):
    """Print out cloudformation metrics for a lambda function.

    :param awsclient
    :param name: name of the lambda function
    :return: exit_code
    """
    metrics = ['Duration', 'Errors', 'Invocations', 'Throttles']
    client_cw = awsclient.get_client('cloudwatch')
    for metric in metrics:
        response = client_cw.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName=metric,
            Dimensions=[
                {
                    'Name': 'FunctionName',
                    'Value': name
                },
            ],
            #StartTime=datetime.now() + timedelta(days=-1),
            #EndTime=datetime.now(),
            StartTime=maya.now().subtract(days=1).datetime(),
            EndTime=maya.now().datetime(),
            Period=3600,
            Statistics=[
                'Sum',
            ],
            Unit=unit(metric)
        )
        print('\t%s %s' % (metric,
                           repr(aggregate_datapoints(response['Datapoints']))))
    return 0


def rollback(awsclient, function_name, alias_name=ALIAS_NAME, version=None):
    """Rollback a lambda function to a given version.

    :param awsclient:
    :param function_name:
    :param alias_name:
    :param version:
    :return: exit_code
    """
    if version:
        print('rolling back to version {}'.format(version))
    else:
        print('rolling back to previous version')
        version = _get_previous_version(awsclient, function_name, alias_name)
        if version == '0':
            print('unable to find previous version of lambda function')
            return 1

        print('new version is %s' % str(version))

    _update_alias(awsclient, function_name, version, alias_name)
    return 0


def delete_lambda(awsclient, function_name, s3_event_sources=[],
                  time_event_sources=[]):
    # FIXME: mutable default arguments!
    """Delete a lambda function.

    :param awsclient:
    :param function_name:
    :param s3_event_sources:
    :param time_event_sources:
    :return: exit_code
    """
    unwire(awsclient, function_name, s3_event_sources=s3_event_sources,
           time_event_sources=time_event_sources,
           alias_name=ALIAS_NAME)
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.delete_function(FunctionName=function_name)

    # TODO remove event source first and maybe also needed for permissions
    print(json2table(response))
    return 0


def info(awsclient, function_name, s3_event_sources=None,
         time_event_sources=None, alias_name=ALIAS_NAME):
    if s3_event_sources is None:
        s3_event_sources = []
    if time_event_sources is None:
        time_event_sources = []
    if not lambda_exists(awsclient, function_name):
        print(colored.red('The function you try to display doesn\'t ' +
                          'exist... Bailing out...'))
        return 1

    client_lambda = awsclient.get_client('lambda')
    lambda_function = client_lambda.get_function(FunctionName=function_name)
    lambda_alias = client_lambda.get_alias(FunctionName=function_name,
                                           Name=alias_name)
    lambda_arn = lambda_alias['AliasArn']

    if lambda_function is not None:
        print(json2table(lambda_function['Configuration']).encode('utf-8'))
        print(json2table(lambda_alias).encode('utf-8'))
        print("\n### PERMISSIONS ###\n")

        try:
            result = client_lambda.get_policy(FunctionName=function_name,
                                              Qualifier=alias_name)

            policy = json.loads(result['Policy'])
            for statement in policy['Statement']:
                print('{} ({}) -> {}'.format(
                    statement['Condition']['ArnLike']['AWS:SourceArn'],
                    statement['Principal']['Service'],
                    statement['Resource']
                ))
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("No permissions found!")
            else:
                raise e

        print("\n### EVENT SOURCES ###\n")

        # S3 Events
        client_s3 = awsclient.get_client('s3')
        for s3_event_source in s3_event_sources:
            bucket_name = s3_event_source.get('bucket')
            print('- \tS3: %s' % bucket_name)
            bucket_notification = client_s3.get_bucket_notification(
                Bucket=bucket_name)
            filter_rules = build_filter_rules(
                s3_event_source.get('prefix', None),
                s3_event_source.get('suffix', None))
            response = client_s3.get_bucket_notification_configuration(
                Bucket=bucket_name)
            if 'LambdaFunctionConfigurations' in response:
                relevant_configs, irrelevant_configs = \
                    filter_bucket_notifications_with_arn(
                        response['LambdaFunctionConfigurations'],
                        lambda_arn, filter_rules
                    )
                if len(relevant_configs) > 0:
                    for config in relevant_configs:
                        print('\t\t{}:'.format(config['Events'][0]))
                        for rule in config['Filter']['Key']['FilterRules']:
                            print('\t\t{}: {}'.format(rule['Name'],
                                                      rule['Value']))
                else:
                    print('\tNot attached')

                    # TODO Beautify
                    # wrapper = TextWrapper(initial_indent='\t', subsequent_indent='\t')
                    # output = "\n".join(wrapper.wrap(json.dumps(config, indent=True)))
                    # print(json.dumps(config, indent=True))
            else:
                print('\tNot attached')

        # CloudWatch Event
        client_events = awsclient.get_client('events')
        for time_event in time_event_sources:
            rule_name = time_event.get('ruleName')
            print('- \tCloudWatch: %s' % rule_name)
            try:
                rule_response = client_events.describe_rule(Name=rule_name)
                target_list = client_events.list_targets_by_rule(
                    Rule=rule_name,
                )["Targets"]
                if target_list:
                    print("\t\tSchedule expression: {}".format(
                        rule_response['ScheduleExpression']))
                for target in target_list:
                    print(
                        '\t\tId: {} -> {}'.format(target['Id'], target['Arn']))
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print('\tNot attached!')
                else:
                    raise e


def filter_bucket_notifications_with_arn(lambda_function_configurations,
                                         lambda_arn, filter_rules=False):
    matching_notifications = []
    not_matching_notifications = []
    for notification in lambda_function_configurations:
        if notification["LambdaFunctionArn"] == lambda_arn:
            if filter_rules:
                existing_filter = notification['Filter']['Key']['FilterRules']
                if list_of_dict_equals(filter_rules, existing_filter):
                    matching_notifications.append(notification)
                else:
                    not_matching_notifications.append(notification)
            else:
                matching_notifications.append(notification)
        else:
            not_matching_notifications.append(notification)
    return matching_notifications, not_matching_notifications


def _ensure_s3_event(awsclient, s3_event_source, function_name, alias_name,
                     target_lambda_arn, ensure="exists"):
    if ensure not in ENSURE_OPTIONS:
        print("{} is invalid ensure option, should be {}".format(ensure,
                                                                 ENSURE_OPTIONS))

    client_s3 = awsclient.get_client('s3')

    bucket_name = s3_event_source.get('bucket')
    event_type = s3_event_source.get('type')
    prefix = s3_event_source.get('prefix', None)
    suffix = s3_event_source.get('suffix', None)

    rule_exists = False
    filter_rules = build_filter_rules(prefix, suffix)

    bucket_configurations = client_s3.get_bucket_notification_configuration(
        Bucket=bucket_name)
    bucket_configurations.pop('ResponseMetadata')
    matching_notifications, not_matching_notifications = filter_bucket_notifications_with_arn(
        bucket_configurations.get('LambdaFunctionConfigurations', []),
        target_lambda_arn, filter_rules)

    for config in matching_notifications:
        if config['Events'][0] == event_type:
            if filter_rules:
                if list_of_dict_equals(filter_rules,
                                       config['Filter']['Key']['FilterRules']):
                    rule_exists = True
            else:
                rule_exists = True
    # permissions_exists
    permission_exists = False
    if rule_exists:
        policies = _get_lambda_policies(awsclient, function_name, alias_name)
        if policies:
            for statement in policies['Statement']:
                if statement['Principal']['Service'] == 's3.amazonaws.com':
                    permission_bucket = get_bucket_from_s3_arn(
                        statement['Condition']['ArnLike']['AWS:SourceArn'])
                    if permission_bucket == bucket_name:
                        permission_exists = statement['Sid']
                        break

    if not rule_exists and not permission_exists:
        if ensure == "exists":
            print(colored.magenta(
                "\tWiring rule {}: {}".format(bucket_name, event_type)))
            for rule in filter_rules:
                print(colored.magenta(
                    '\t\t{}: {}'.format(rule['Name'], rule['Value'])))
            _wire_s3_to_lambda(awsclient, s3_event_source, function_name,
                               target_lambda_arn)
        elif ensure == "absent":
            return 0
    if rule_exists and permission_exists:
        if ensure == "absent":
            print(colored.magenta(
                "\tRemoving rule {}: {}".format(bucket_name, event_type)))
            for rule in filter_rules:
                print(colored.magenta(
                    '\t\t{}: {}'.format(rule['Name'], rule['Value'])))
            _remove_permission(awsclient, function_name, permission_exists, alias_name)
            _remove_events_from_s3_bucket(awsclient, bucket_name, target_lambda_arn,
                                          filter_rules)


def _ensure_cloudwatch_event(awsclient, time_event, function_name,
                             alias_name, lambda_arn, ensure='exists'):
    if not ensure in ENSURE_OPTIONS:
        print("{} is invalid ensure option, should be {}".format(ensure,
                                                                 ENSURE_OPTIONS))
        # TODO unbelievable: another sys.exit in library code!!!
        sys.exit(1)
    rule_name = time_event.get('ruleName')
    rule_description = time_event.get('ruleDescription')
    schedule_expression = time_event.get('scheduleExpression')
    client_event = awsclient.get_client('events')

    rule_exists = False
    schedule_expression_match = False
    not_matching_schedule_expression = None
    try:
        rule_response = client_event.describe_rule(Name=rule_name)
        rule_exists = True
        if rule_response['ScheduleExpression'] == schedule_expression:
            schedule_expression_match = True
        else:
            not_matching_schedule_expression = rule_response[
                'ScheduleExpression']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            pass
        else:
            raise e

    permission_exists = False
    if rule_exists:
        policies = _get_lambda_policies(awsclient, function_name, alias_name)
        if policies:
            for statement in policies['Statement']:
                if statement['Principal']['Service'] == 'events.amazonaws.com':
                    event_source_arn = get_rule_name_from_event_arn(
                        statement['Condition']['ArnLike']['AWS:SourceArn'])
                    if rule_name == event_source_arn:
                        permission_exists = statement['Sid']
                        break

    if not rule_exists and not permission_exists:
        if ensure == 'exists':
            print(colored.magenta(
                "\tWiring Cloudwatch event {}\n\t\t{}".format(rule_name,
                                                              schedule_expression)))
            rule_arn = _lambda_add_time_schedule_event_source(
                awsclient, rule_name, rule_description, schedule_expression,
                lambda_arn)
            _lambda_add_invoke_permission(
                awsclient, function_name, 'events.amazonaws.com', rule_arn)
        elif ensure == 'absent':
            return 0
    if rule_exists and permission_exists:
        if ensure == 'exists':
            if schedule_expression_match:
                return 0
            else:
                print(colored.magenta(
                    "\t Updating Cloudwatch event {}\n\t\tOld: {}\n\t\tTo: {}".format(
                        rule_name,
                        not_matching_schedule_expression,
                        schedule_expression)))
                rule_arn = _lambda_add_time_schedule_event_source(
                    awsclient, rule_name, rule_description,
                    schedule_expression, lambda_arn)
        if ensure == 'absent':
            print(colored.magenta("\tRemoving rule {}\n\t\t{}".format(rule_name,
                                                                      schedule_expression)))
            _remove_permission(awsclient, function_name, statement['Sid'],
                               alias_name)
            _remove_cloudwatch_rule_event(awsclient, rule_name, lambda_arn)


def _wire_s3_to_lambda(awsclient, s3_event_source, function_name,
                       target_lambda_arn):
    bucket_name = s3_event_source.get('bucket')
    event_type = s3_event_source.get('type')
    prefix = s3_event_source.get('prefix', None)
    suffix = s3_event_source.get('suffix', None)
    s3_arn = create_aws_s3_arn(bucket_name)

    _lambda_add_invoke_permission(awsclient, function_name,
                                  's3.amazonaws.com', s3_arn)
    _lambda_add_s3_event_source(awsclient, target_lambda_arn, event_type,
                                bucket_name, prefix, suffix)


def wire(awsclient, function_name, s3_event_sources=None,
         time_event_sources=None,
         alias_name=ALIAS_NAME):
    """Wiring a lambda function to events.

    :param awsclient:
    :param function_name:
    :param s3_event_sources:
    :param time_event_sources:
    :param alias_name:
    :return: exit_code
    """
    if not lambda_exists(awsclient, function_name):
        print(colored.red('The function you try to wire up doesn\'t ' +
                          'exist... Bailing out...'))
        return 1
    client_lambda = awsclient.get_client('lambda')
    lambda_function = client_lambda.get_function(FunctionName=function_name)
    lambda_arn = client_lambda.get_alias(FunctionName=function_name,
                                         Name=alias_name)['AliasArn']
    print('wiring lambda_arn %s ...' % lambda_arn)

    if lambda_function is not None:
        s3_events_ensure_exists, s3_events_ensure_absent = filter_events_ensure(
            s3_event_sources)
        cloudwatch_events_ensure_exists, cloudwatch_events_ensure_absent = \
            filter_events_ensure(time_event_sources)

        for s3_event_source in s3_events_ensure_absent:
            _ensure_s3_event(awsclient, s3_event_source, function_name,
                             alias_name, lambda_arn, s3_event_source['ensure'])
        for s3_event_source in s3_events_ensure_exists:
            _ensure_s3_event(awsclient, s3_event_source, function_name,
                             alias_name, lambda_arn, s3_event_source['ensure'])

        for time_event in cloudwatch_events_ensure_absent:
            _ensure_cloudwatch_event(awsclient, time_event, function_name,
                                     alias_name, lambda_arn,
                                     time_event['ensure'])
        for time_event in cloudwatch_events_ensure_exists:
            _ensure_cloudwatch_event(awsclient, time_event, function_name,
                                     alias_name, lambda_arn,
                                     time_event['ensure'])
    return 0


def filter_events_ensure(event_sources):
    events_ensure_exists = []
    events_ensure_absent = []
    for event in event_sources:
        if 'ensure' in event:
            if event['ensure'] == 'exists':
                events_ensure_exists.append(event)
            elif event['ensure'] == 'absent':
                events_ensure_absent.append(event)
            else:
                print(colored.red(
                    'Ensure must be one of {}, currently set to {}'.format(
                        ENSURE_OPTIONS, event['ensure'])))
                # FIXME exit in lib code!
                # TODO: make sure it has a test!
                # TODO unbelievable: another sys.exit in library code!!!
                sys.exit(1)
        else:
            event['ensure'] = 'exists'
            events_ensure_exists.append(event)
    return events_ensure_exists, events_ensure_absent


def _get_lambda_policies(awsclient, function_name, alias_name):
    client_lambda = awsclient.get_client('lambda')
    policies = None
    try:
        result = client_lambda.get_policy(FunctionName=function_name,
                                          Qualifier=alias_name)
        policies = json.loads(result['Policy'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(colored.red("Permission policies not found"))
        else:
            raise e
    return policies


def unwire(awsclient, function_name, s3_event_sources=None,
           time_event_sources=None,
           alias_name=ALIAS_NAME):
    """Unwire an event from a lambda function.

    :param awsclient:
    :param function_name:
    :param s3_event_sources:
    :param time_event_sources:
    :param alias_name:
    :return: exit_code
    """
    if not lambda_exists(awsclient, function_name):
        print(colored.red('The function you try to wire up doesn\'t ' +
                          'exist... Bailing out...'))
        return 1

    client_lambda = awsclient.get_client('lambda')
    lambda_function = client_lambda.get_function(FunctionName=function_name)
    lambda_arn = client_lambda.get_alias(FunctionName=function_name,
                                         Name=alias_name)['AliasArn']
    print('UN-wiring lambda_arn %s ' % lambda_arn)
    policies = None
    try:
        result = client_lambda.get_policy(FunctionName=function_name,
                                          Qualifier=alias_name)
        policies = json.loads(result['Policy'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("Permission policies not found")
        else:
            raise e

    if lambda_function is not None:
        #### S3 Events
        # for every permission - delete it and corresponding rule (if exists)
        if policies:
            for statement in policies['Statement']:
                if statement['Principal']['Service'] == 's3.amazonaws.com':
                    source_bucket = get_bucket_from_s3_arn(
                        statement['Condition']['ArnLike']['AWS:SourceArn'])
                    print('\tRemoving S3 permission {} invoking {}'.format(
                        source_bucket, lambda_arn))
                    _remove_permission(awsclient, function_name,
                                       statement['Sid'], alias_name)
                    print('\tRemoving All S3 events {} invoking {}'.format(
                        source_bucket, lambda_arn))
                    _remove_events_from_s3_bucket(awsclient, source_bucket,
                                                  lambda_arn)

        # Case: s3 events without permissions active "safety measure"
        for s3_event_source in s3_event_sources:
            bucket_name = s3_event_source.get('bucket')
            _remove_events_from_s3_bucket(awsclient, bucket_name, lambda_arn)

        #### CloudWatch Events
        # for every permission - delete it and corresponding rule (if exists)
        if policies:
            for statement in policies['Statement']:
                if statement['Principal']['Service'] == 'events.amazonaws.com':
                    rule_name = get_rule_name_from_event_arn(
                        statement['Condition']['ArnLike']['AWS:SourceArn'])
                    print(
                        '\tRemoving Cloudwatch permission {} invoking {}'.format(
                            rule_name, lambda_arn))
                    _remove_permission(awsclient, function_name,
                                       statement['Sid'], alias_name)
                    print('\tRemoving Cloudwatch rule {} invoking {}'.format(
                        rule_name, lambda_arn))
                    _remove_cloudwatch_rule_event(awsclient, rule_name,
                                                  lambda_arn)
        # Case: rules without permissions active, "safety measure"
        for time_event in time_event_sources:
            rule_name = time_event.get('ruleName')
            _remove_cloudwatch_rule_event(awsclient, rule_name, lambda_arn)

    return 0


def _remove_cloudwatch_rule_event(awsclient, rule_name, target_lambda_arn):
    client_event = awsclient.get_client('events')
    try:
        target_list = client_event.list_targets_by_rule(
            Rule=rule_name,
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return
        else:
            raise e
    target_id_list = []

    for target in target_list['Targets']:
        if target['Arn'] == target_lambda_arn:
            target_id_list += [target['Id']]
    # remove targets
    if target_id_list:
        client_event.remove_targets(
            Rule=rule_name,
            Ids=target_id_list,
        )
    # Delete rule only if all targets were associated with target_arn (i.e. only target target_arn function)
    if len(target_id_list) == len(target_list['Targets']) or (
                not target_id_list and not target_list):
        client_event.delete_rule(
            Name=rule_name
        )


def _remove_events_from_s3_bucket(awsclient, bucket_name, target_lambda_arn,
                                  filter_rule=False):
    client_s3 = awsclient.get_client('s3')
    bucket_configurations = client_s3.get_bucket_notification_configuration(
        Bucket=bucket_name)
    bucket_configurations.pop('ResponseMetadata')
    matching_notifications, not_matching_notifications = \
        filter_bucket_notifications_with_arn(
            bucket_configurations.get('LambdaFunctionConfigurations', []),
            target_lambda_arn, filter_rule
        )
    if not_matching_notifications:
        bucket_configurations[
            'LambdaFunctionConfigurations'] = not_matching_notifications
    else:
        if 'LambdaFunctionConfigurations' in bucket_configurations:
            bucket_configurations.pop('LambdaFunctionConfigurations')

    response = client_s3.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration=bucket_configurations
    )


def _remove_permission(awsclient, function_name, statement_id, qualifier):
    client_lambda = awsclient.get_client('lambda')
    response_remove = client_lambda.remove_permission(
        FunctionName=function_name,
        StatementId=statement_id,
        Qualifier=qualifier
    )


def cleanup_bundle():
    """Deletes files used for creating bundle.
        * vendored/*
        * bundle.zip
    """
    paths = ['./vendored', './bundle.zip']
    for path in paths:
        if os.path.exists(path):
            log.debug("Deleting %s..." % path)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)


def ping(awsclient, function_name, alias_name=ALIAS_NAME, version=None):
    """Send a ping request to a lambda function.

    :param awsclient:
    :param function_name:
    :param alias_name:
    :param version:
    :return: ping response payload
    """
    log.debug('sending ping to lambda function: %s', function_name)
    payload = '{"ramuda_action": "ping"}'  # default to ping event
    # reuse invoke
    return invoke(awsclient, function_name, payload, invocation_type=None,
           alias_name=alias_name, version=version)


def invoke(awsclient, function_name, payload, invocation_type=None,
           alias_name=ALIAS_NAME, version=None, outfile=None):
    """Send a ping request to a lambda function.

    :param awsclient:
    :param function_name:
    :param payload:
    :param invocation_type:
    :param alias_name:
    :param version:
    :param outfile: write response to file
    :return: ping response payload
    """
    log.debug('invoking lambda function: %s', function_name)
    client_lambda = awsclient.get_client('lambda')
    if invocation_type is None:
        invocation_type = 'RequestResponse'
    if payload.startswith('file:/'):
        log.debug('reading payload from file: %s' % payload)
        with open(payload[6:], 'r') as pfile:
            payload = pfile.read()

    if version:
        response = client_lambda.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,
            Payload=payload,
            Qualifier=version
        )
    else:
        response = client_lambda.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,
            Payload=payload,
            Qualifier=alias_name
        )

    results = response['Payload'].read()  # payload is a 'StreamingBody'
    if 'alive' in str(results):
        print(str(results))
        print('#####Cool, your lambda function did respond to ping with %s.' %
              str(results))
    else:
        print(colored.red('Your lambda function did not respond to ping.'))
    log.debug('invoke completed')
    # write to file
    if outfile:
        with open(outfile, 'w') as ofile:
            ofile.write(str(results))
            ofile.flush()
        return
    else:
        return results
