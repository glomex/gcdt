# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import json
import time

from clint.textui import colored
from clint.packages.colorama import Fore

from .s3 import upload_file_to_s3
from .gcdt_logging import getLogger
from .cloudwatch_logs import get_log_events, datetime_to_timestamp, \
    check_log_stream_exists


log = getLogger(__name__)


def deploy(awsclient, applicationName, deploymentGroupName,
           deploymentConfigName, bucket, bundlefile):
    """Upload bundle and deploy to deployment group.
    This includes the bundle-action.

    :param applicationName:
    :param deploymentGroupName:
    :param deploymentConfigName:
    :param bucket:
    :param bundlefile:
    :return: deploymentId from create_deployment
    """
    etag, version = upload_file_to_s3(awsclient, bucket,
                                      _build_bundle_key(applicationName),
                                      bundlefile)

    client_codedeploy = awsclient.get_client('codedeploy')
    response = client_codedeploy.create_deployment(
        applicationName=applicationName,
        deploymentGroupName=deploymentGroupName,
        revision={
            'revisionType': 'S3',
            's3Location': {
                'bucket': bucket,
                'key': _build_bundle_key(applicationName),
                'bundleType': 'tgz',
                'eTag': etag,
                'version': version,
            },
        },
        deploymentConfigName=deploymentConfigName,
        description='deploy with tenkai',
        ignoreApplicationStopFailures=True
    )

    log.info(
        "Deployment: {} -> URL: https://{}.console.aws.amazon.com/codedeploy/home?region={}#/deployments/{}".format(
            Fore.MAGENTA + response['deploymentId'] + Fore.RESET,
            client_codedeploy.meta.region_name,
            client_codedeploy.meta.region_name,
            response['deploymentId'],
        ))

    return response['deploymentId']


def _build_bundle_key(application_name):
    # key = bundle name on target
    return '%s/bundle.tar.gz' % application_name


def output_deployment_status(awsclient, deployment_id, iterations=100):
    """Wait until an deployment is in an steady state and output information.

    :param deployment_id:
    :param iterations:
    :return: exit_code
    """
    counter = 0
    steady_states = ['Succeeded', 'Failed', 'Stopped']
    client_codedeploy = awsclient.get_client('codedeploy')

    while counter <= iterations:
        response = client_codedeploy.get_deployment(deploymentId=deployment_id)
        status = response['deploymentInfo']['status']

        if status not in steady_states:
            log.info('Deployment: %s - State: %s' % (deployment_id, status))
            time.sleep(10)
        elif status == 'Failed':
            log.info(
                colored.red('Deployment: {} failed: {}'.format(
                    deployment_id,
                    json.dumps(response['deploymentInfo']['errorInformation'],
                               indent=2)
                ))
            )
            return 1
        else:
            log.info('Deployment: %s - State: %s' % (deployment_id, status))
            break

    return 0


def stop_deployment(awsclient, deployment_id):
    """stop tenkai deployment.

    :param awsclient:
    :param deployment_id:
    """
    log.info('Deployment: %s - stopping active deployment.', deployment_id)
    client_codedeploy = awsclient.get_client('codedeploy')

    response = client_codedeploy.stop_deployment(
        deploymentId=deployment_id,
        autoRollbackEnabled=True
    )


def _list_deployment_instances(awsclient, deployment_id):
    """list deployment instances.

    :param awsclient:
    :param deployment_id:
    """
    client_codedeploy = awsclient.get_client('codedeploy')

    instances = []
    next_token = None

    # TODO refactor generic exhaust_function from this
    while True:
        request = {
            'deploymentId': deployment_id
        }
        if next_token:
            request['nextToken'] = next_token
        response = client_codedeploy.list_deployment_instances(**request)
        instances.extend(response['instancesList'])
        if 'nextToken' not in response:
            break
        next_token = response['nextToken']
    return instances


def _get_deployment_instance_summary(awsclient, deployment_id, instance_id):
    """instance summary.

    :param awsclient:
    :param deployment_id:
    :param instance_id:
    return: status, last_event
    """
    client_codedeploy = awsclient.get_client('codedeploy')
    request = {
        'deploymentId': deployment_id,
        'instanceId': instance_id
    }
    response = client_codedeploy.get_deployment_instance(**request)
    return response['instanceSummary']['status'], \
           response['instanceSummary']['lifecycleEvents'][-1]['lifecycleEventName']


def _get_deployment_instance_diagnostics(awsclient, deployment_id, instance_id):
    """Gets you the diagnostics details for the first 'Failed' event.

    :param awsclient:
    :param deployment_id:
    :param instance_id:
    return: None or (error_code, script_name, message, log_tail)
    """
    client_codedeploy = awsclient.get_client('codedeploy')
    request = {
        'deploymentId': deployment_id,
        'instanceId': instance_id
    }
    response = client_codedeploy.get_deployment_instance(**request)
    # find first 'Failed' event
    for i, event in enumerate(response['instanceSummary']['lifecycleEvents']):
        if event['status'] == 'Failed':
            return event['diagnostics']['errorCode'], \
                   event['diagnostics']['scriptName'], \
                   event['diagnostics']['message'], \
                   event['diagnostics']['logTail']
    return None


def output_deployment_summary(awsclient, deployment_id):
    """summary

    :param awsclient:
    :param deployment_id:
    """
    log.info('\ndeployment summary:')
    log.info('%-22s %-12s %s', 'Instance ID', 'Status', 'Most recent event')
    for instance_id in _list_deployment_instances(awsclient, deployment_id):
        status, last_event = \
            _get_deployment_instance_summary(awsclient, deployment_id, instance_id)
        log.info(Fore.MAGENTA + '%-22s' + Fore.RESET + ' %-12s %s',
                 instance_id, status, last_event)


def output_deployment_diagnostics(awsclient, deployment_id, log_group, start_time=None):
    """diagnostics

    :param awsclient:
    :param deployment_id:
    """
    headline = False
    for instance_id in _list_deployment_instances(awsclient, deployment_id):
        diagnostics = _get_deployment_instance_diagnostics(
            awsclient, deployment_id, instance_id)
        #if error_code != 'Success':
        if diagnostics is not None:
            error_code, script_name, message, log_tail = diagnostics
            # header
            if not headline:
                headline = True
                log.info('\ndeployment diagnostics:')
            # event logs
            log.info('Instance ID: %s', Fore.MAGENTA + instance_id + Fore.RESET)
            log.info('Error Code:  %s', error_code)
            log.info('Script Name: %s', script_name)
            log.info('Message:     %s', message)
            log.info('Log Tail:    %s', log_tail)
            # cloudwatch logs
            if check_log_stream_exists(awsclient, log_group, instance_id):
                logentries = get_log_events(
                    awsclient, log_group, instance_id,
                    datetime_to_timestamp(start_time))
                if logentries:
                    log.info('instance %s logentries', instance_id)
                    for e in logentries:
                        log.info(e['message'].strip())
