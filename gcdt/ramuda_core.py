# -*- coding: utf-8 -*-

"""ramuda.
Deploy Lambda functions to AWS
"""

from __future__ import unicode_literals, print_function

import json
import logging
import shutil
import time

import maya
import os
from botocore.exceptions import ClientError as ClientError
from clint.textui import colored

from gcdt.ramuda_utils import filter_bucket_notifications_with_arn
from gcdt.ramuda_wire import unwire, unwire_deprecated
from .cloudwatch_logs import put_retention_policy, delete_log_group, \
    filter_log_events, decode_format_timestamp, datetime_to_timestamp
from .ramuda_utils import s3_upload, \
    lambda_exists, create_sha256, get_remote_code_hash, unit, \
    aggregate_datapoints, build_filter_rules
from .utils import GracefulExit, json2table

log = logging.getLogger(__name__)
ALIAS_NAME = 'ACTIVE'


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
    except GracefulExit:
        raise
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
    except GracefulExit:
        raise
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


def list_functions(awsclient):
    """List the deployed lambda functions and print configuration.

    :return: exit_code
    """
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.list_functions()
    for function in response['Functions']:
        log.info(function['FunctionName'])
        log.info('\t' 'Memory: ' + str(function['MemorySize']))
        log.info('\t' 'Timeout: ' + str(function['Timeout']))
        log.info('\t' 'Role: ' + str(function['Role']))
        log.info('\t' 'Current Version: ' + str(function['Version']))
        log.info('\t' 'Last Modified: ' + str(function['LastModified']))
        log.info('\t' 'CodeSha256: ' + str(function['CodeSha256']))

        log.info('\n')
    return 0


def deploy_lambda(awsclient, function_name, role, handler_filename,
                  handler_function,
                  folders, description, timeout, memory, subnet_ids=None,
                  security_groups=None, artifact_bucket=None,
                  zipfile=None,
                  fail_deployment_on_unsuccessful_ping=False,
                  runtime='python2.7', settings=None, environment=None,
                  retention_in_days=None
                  ):
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
    :param environment: environment variables
    :param retention_in_days: retention time of the cloudwatch logs
    :return: exit_code
    """
    # TODO: the signature of this function is too big, clean this up
    # also consolidate create, update, config and add waiters!
    if lambda_exists(awsclient, function_name):
        function_version = _update_lambda(awsclient, function_name,
                                          handler_filename,
                                          handler_function, folders, role,
                                          description, timeout, memory,
                                          subnet_ids, security_groups,
                                          artifact_bucket=artifact_bucket,
                                          zipfile=zipfile,
                                          environment=environment
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
                                          runtime=runtime,
                                          environment=environment)
    # configure cloudwatch logs
    if retention_in_days:
        log_group_name = '/aws/lambda/%s' % function_name
        put_retention_policy(awsclient, log_group_name, retention_in_days)

    pong = ping(awsclient, function_name, version=function_version)
    if 'alive' in str(pong):
        log.info(colored.green('Great you\'re already accepting a ping ' +
                            'in your Lambda function'))
    elif fail_deployment_on_unsuccessful_ping and not 'alive' in pong:
        log.info(colored.red('Pinging your lambda function failed'))
        # we do not deploy alias and fail command
        return 1
    else:
        log.info(colored.red('Please consider adding a reaction to a ' +
                          'ping event to your lambda function'))
    _deploy_alias(awsclient, function_name, function_version)
    return 0


def _create_lambda(awsclient, function_name, role, handler_filename,
                   handler_function,
                   folders, description, timeout, memory,
                   subnet_ids=None, security_groups=None,
                   artifact_bucket=None, zipfile=None, runtime='python2.7',
                   environment=None):
    log.debug('create lambda function: %s' % function_name)
    # move to caller!
    # _install_dependencies_with_pip('requirements.txt', './vendored')
    client_lambda = awsclient.get_client('lambda')
    # print ('creating function %s with role %s handler %s folders %s timeout %s memory %s') % (
    # function_name, role, handler_filename, str(folders), str(timeout), str(memory))
    if environment is None:
        environment = {}

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
            Publish=True,
            Environment={
                'Variables': environment
            }
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
            Publish=True,
            Environment={
                'Variables': environment
            }
        )
    else:
        log.debug('no zipfile and no artifact_bucket -> nothing to do!')
        # no zipfile and no artifact_bucket -> nothing to do!
        return
    log.debug('lambda create completed...')

    function_version = response['Version']
    log.info(json2table(response))
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
                   zipfile=None, environment=None
                   ):
    log.debug('update lambda function: %s', function_name)
    _update_lambda_function_code(awsclient, function_name,
                                 artifact_bucket=artifact_bucket,
                                 zipfile=zipfile
                                 )
    function_version = \
        _update_lambda_configuration(
            awsclient, function_name, role, handler_function,
            description, timeout, memory, subnet_ids, security_groups,
            environment
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
    log.info('Finished - a bundle.zip is waiting for you...')
    return 0


def _update_lambda_function_code(
        awsclient, function_name,
        artifact_bucket=None,
        zipfile=None
):
    log.debug('Updating existing AWS Lambda function...')
    client_lambda = awsclient.get_client('lambda')
    if not zipfile:
        return 1
    local_hash = create_sha256(zipfile)
    log.debug('local_hash: %s', local_hash)

    remote_hash = get_remote_code_hash(awsclient, function_name)
    log.debug('remote_hash: %s', remote_hash)
    if local_hash == remote_hash:
        log.warn('AWS Lambda code hasn\'t changed - won\'t upload code bundle')
    else:
        if not artifact_bucket:
            log.warn('no stack bucket found')
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
        log.info(json2table(response))
    return 0


def _update_lambda_configuration(awsclient, function_name, role,
                                 handler_function,
                                 description, timeout, memory, subnet_ids=None,
                                 security_groups=None, environment=None):
    log.info('Update AWS Lambda configuration for function: %s' % function_name)
    client_lambda = awsclient.get_client('lambda')

    if environment is None:
        environment = {}

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
            },
            Environment={
                'Variables': environment
            }
        )
        log.info(json2table(response))
    else:
        response = client_lambda.update_function_configuration(
            FunctionName=function_name,
            Role=role,
            Handler=handler_function,
            Description=description,
            Timeout=timeout,
            MemorySize=memory,
            Environment={
                'Variables': environment
            })

        log.info(json2table(response))
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
            # StartTime=datetime.now() + timedelta(days=-1),
            # EndTime=datetime.now(),
            StartTime=maya.now().subtract(days=1).datetime(),
            EndTime=maya.now().datetime(),
            Period=3600,
            Statistics=[
                'Sum',
            ],
            Unit=unit(metric)
        )
        log.info('\t%s %s' % (metric,
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
        log.info('rolling back to version {}'.format(version))
    else:
        log.info('rolling back to previous version')
        version = _get_previous_version(awsclient, function_name, alias_name)
        if version == '0':
            log.error('unable to find previous version of lambda function')
            return 1

        log.info('new version is %s' % str(version))

    _update_alias(awsclient, function_name, version, alias_name)
    return 0


def delete_lambda(awsclient, function_name, events=None, delete_logs=False):
    """Delete a lambda function.

    :param awsclient:
    :param function_name:
    :param events: list of events
    :param delete_logs:
    :return: exit_code
    """
    if events is not None:
        unwire(awsclient, events, function_name, alias_name=ALIAS_NAME)
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.delete_function(FunctionName=function_name)
    if delete_logs:
        log_group_name = '/aws/lambda/%s' % function_name
        delete_log_group(awsclient, log_group_name)

    # TODO remove event source first and maybe also needed for permissions
    log.info(json2table(response))
    return 0


def delete_lambda_deprecated(awsclient, function_name, s3_event_sources=[],
                             time_event_sources=[], delete_logs=False):
    # FIXME: mutable default arguments!
    """Deprecated: please use delete_lambda!

    :param awsclient:
    :param function_name:
    :param s3_event_sources:
    :param time_event_sources:
    :param delete_logs:
    :return: exit_code
    """
    unwire_deprecated(awsclient, function_name, s3_event_sources=s3_event_sources,
                      time_event_sources=time_event_sources,
                      alias_name=ALIAS_NAME)
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.delete_function(FunctionName=function_name)
    if delete_logs:
        log_group_name = '/aws/lambda/%s' % function_name
        delete_log_group(awsclient, log_group_name)

    # TODO remove event source first and maybe also needed for permissions
    log.info(json2table(response))
    return 0


def info(awsclient, function_name, s3_event_sources=None,
         time_event_sources=None, alias_name=ALIAS_NAME):
    if s3_event_sources is None:
        s3_event_sources = []
    if time_event_sources is None:
        time_event_sources = []
    if not lambda_exists(awsclient, function_name):
        log.error(colored.red('The function you try to display doesn\'t ' +
                          'exist... Bailing out...'))
        return 1

    client_lambda = awsclient.get_client('lambda')
    lambda_function = client_lambda.get_function(FunctionName=function_name)
    lambda_alias = client_lambda.get_alias(FunctionName=function_name,
                                           Name=alias_name)
    lambda_arn = lambda_alias['AliasArn']

    if lambda_function is not None:
        log.info(json2table(lambda_function['Configuration']).encode('utf-8'))
        log.info(json2table(lambda_alias).encode('utf-8'))
        log.info("\n### PERMISSIONS ###\n")

        try:
            result = client_lambda.get_policy(FunctionName=function_name,
                                              Qualifier=alias_name)

            policy = json.loads(result['Policy'])
            for statement in policy['Statement']:
                log.info('{} ({}) -> {}'.format(
                    statement['Condition']['ArnLike']['AWS:SourceArn'],
                    statement['Principal']['Service'],
                    statement['Resource']
                ))
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                log.info("No permissions found!")
            else:
                raise e

        log.info("\n### EVENT SOURCES ###\n")

        # S3 Events
        client_s3 = awsclient.get_client('s3')
        for s3_event_source in s3_event_sources:
            bucket_name = s3_event_source.get('bucket')
            log.info('- \tS3: %s' % bucket_name)
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
                        log.info('\t\t{}:'.format(config['Events'][0]))
                        for rule in config['Filter']['Key']['FilterRules']:
                            log.info('\t\t{}: {}'.format(rule['Name'],
                                                      rule['Value']))
                else:
                    log.info('\tNot attached')

                    # TODO Beautify
                    # wrapper = TextWrapper(initial_indent='\t', subsequent_indent='\t')
                    # output = "\n".join(wrapper.wrap(json.dumps(config, indent=True)))
                    # print(json.dumps(config, indent=True))
            else:
                log.info('\tNot attached')

        # CloudWatch Event
        client_events = awsclient.get_client('events')
        for time_event in time_event_sources:
            rule_name = time_event.get('ruleName')
            log.info('- \tCloudWatch: %s' % rule_name)
            try:
                rule_response = client_events.describe_rule(Name=rule_name)
                target_list = client_events.list_targets_by_rule(
                    Rule=rule_name,
                )["Targets"]
                if target_list:
                    log.info("\t\tSchedule expression: {}".format(
                        rule_response['ScheduleExpression']))
                for target in target_list:
                    log.info(
                        '\t\tId: {} -> {}'.format(target['Id'], target['Arn']))
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    log.info('\tNot attached!')
                else:
                    raise e


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
    if payload.startswith('file://'):
        log.debug('reading payload from file: %s' % payload)
        with open(payload[7:], 'r') as pfile:
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
    log.debug('invoke completed')
    # write to file
    if outfile:
        with open(outfile, 'w') as ofile:
            ofile.write(str(results))
            ofile.flush()
        return
    else:
        return results


def logs(awsclient, function_name, start_dt, end_dt=None, tail=False):
    """Send a ping request to a lambda function.

    :param awsclient:
    :param function_name:
    :param start_dt:
    :param end_dt:
    :param tail:
    :return:
    """
    log.debug('Getting cloudwatch logs for: %s', function_name)
    log_group_name = '/aws/lambda/%s' % function_name

    current_date = None
    start_ts = datetime_to_timestamp(start_dt)
    if end_dt:
        end_ts = datetime_to_timestamp(end_dt)
    else:
        end_ts = None

    # tail mode
    # we assume that logs can arrive late but not out of order
    # so we hold the timestamp of the last logentry and start the next iteration
    # from there
    while True:
        logentries = filter_log_events(awsclient, log_group_name,
                                       start_ts=start_ts, end_ts=end_ts)
        if logentries:
            for e in logentries:
                actual_date, actual_time = decode_format_timestamp(e['timestamp'])
                if current_date != actual_date:
                    # print the date only when it changed
                    current_date = actual_date
                    log.info(current_date)
                log.info('%s  %s' % (actual_time, e['message'].strip()))
        if tail:
            if logentries:
                start_ts = logentries[-1]['timestamp'] + 1
            time.sleep(2)
            continue
        break
