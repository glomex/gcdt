# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import json
import time

from clint.textui import colored

from .s3 import upload_file_to_s3
from .gcdt_logging import getLogger


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

    print(
        "Deployment: {} -> URL: https://{}.console.aws.amazon.com/codedeploy/home?region={}#/deployments/{}".format(
            response['deploymentId'],
            client_codedeploy.meta.region_name,
            client_codedeploy.meta.region_name,
            response['deploymentId'],
        ))

    return response['deploymentId']


def _build_bundle_key(application_name):
    # key = bundle name on target
    return '%s/bundle.tar.gz' % application_name


def deployment_status(awsclient, deploymentId, iterations=100):
    """Wait until an deployment is in an steady state and output information.

    :param deploymentId:
    :param iterations:
    :return: exit_code
    """
    counter = 0
    steady_states = ['Succeeded', 'Failed', 'Stopped']
    client_codedeploy = awsclient.get_client('codedeploy')

    while counter <= iterations:
        response = client_codedeploy.get_deployment(deploymentId=deploymentId)
        status = response['deploymentInfo']['status']

        if status not in steady_states:
            log.info('Deployment: %s - State: %s' % (deploymentId, status))
            # sys.stdout.flush()
            time.sleep(10)
        elif status == 'Failed':
            log.info(
                colored.red('Deployment: {} failed: {}'.format(
                    deploymentId,
                    json.dumps(response['deploymentInfo']['errorInformation'],
                               indent=2)
                ))
            )
            return 1
        else:
            log.info('Deployment: %s - State: %s' % (deploymentId, status))
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
