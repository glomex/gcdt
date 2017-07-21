#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The 'tenkai' tool is used to work with AWS CodeDeploy.
"""

from __future__ import unicode_literals, print_function
import os
import sys

import maya

from . import utils
from .gcdt_defaults import DEFAULT_CONFIG
from .tenkai_core import deploy, output_deployment_status, stop_deployment, \
    output_deployment_summary, output_deployment_diagnostics
from gcdt.s3 import prepare_artifacts_bucket
from .gcdt_cmd_dispatcher import cmd
from .utils import GracefulExit
from .gcdt_logging import getLogger
from . import gcdt_lifecycle


log = getLogger(__name__)


DOC = '''Usage:
        tenkai bundle [-v]
        tenkai deploy [-v]
        tenkai version

-h --help           show this
-v --verbose        show debug messages
'''


@cmd(spec=['version'])
def version_cmd():
    utils.version()
    return 1


@cmd(spec=['deploy'])
def deploy_cmd(**tooldata):
    context = tooldata.get('context')
    config = tooldata.get('config')
    awsclient = context.get('_awsclient')
    # in case we fail we limit log output to after start_time
    start_time = maya.now().datetime(naive=True)
    log_group = config.get('deployment', {}).get(
        'LogGroup', DEFAULT_CONFIG['tenkai']['log_group'])

    prepare_artifacts_bucket(awsclient,
                             config['codedeploy'].get('artifactsBucket'))
    # TODO deprecate prebundle hook with reference to new signal-based-hooks
    # TODO and move them to glomex_bundler
    pre_bundle_scripts = config.get('preBundle', None)
    if pre_bundle_scripts:
        exit_code = utils.execute_scripts(pre_bundle_scripts)
        if exit_code != 0:
            log.error('Pre bundle script exited with error')
            return 1

    bucket = config['codedeploy'].get('artifactsBucket')

    try:
        deployment = deploy(
            awsclient=awsclient,
            applicationName=config['codedeploy'].get('applicationName'),
            deploymentGroupName=config['codedeploy'].get('deploymentGroupName'),
            deploymentConfigName=config['codedeploy'].get('deploymentConfigName'),
            bucket=bucket,
            bundlefile=context['_bundle_file']
        )

        exit_code = output_deployment_status(awsclient, deployment)
        output_deployment_summary(awsclient, deployment)
        output_deployment_diagnostics(awsclient, deployment, log_group, start_time)
        if exit_code:
            return 1

    except GracefulExit as e:
        log.warn('Received %s signal - stopping tenkai deployment' % str(e))
        stop_deployment(awsclient, deployment)
        exit_code = 1

    # remove bundle file
    if context['_bundle_file'] and os.path.exists(context['_bundle_file']):
        os.unlink(context['_bundle_file'])

    return exit_code


@cmd(spec=['bundle'])
def bundle_cmd(**tooldata):
    context = tooldata.get('context')
    log.info('created bundle at %s' % context['_bundle_file'])


def main():
    # TODO: register bundle with bundle signals
    sys.exit(
        gcdt_lifecycle.main(DOC, 'tenkai',
                            dispatch_only=['version'])
    )


if __name__ == '__main__':
    main()
