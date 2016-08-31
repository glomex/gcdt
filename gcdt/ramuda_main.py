#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""ramuda.
Script to deploy Lambda functions to AWS
"""

from __future__ import print_function
import sys
from glomex_utils.config_reader import read_lambda_config
from docopt import docopt
from gcdt import utils
from gcdt.logger import setup_logger
from gcdt.ramuda_core import list_functions, get_metrics, deploy_lambda, \
    wire, bundle_lambda, unwire, delete_lambda, rollback, ping
from gcdt.utils import read_gcdt_user_config, get_context, get_command
from gcdt.monitoring import datadog_notification, datadog_error

log = setup_logger(logger_name='ramuda')

# TODO introduce own config for account detection
# TODO reupload on requirements.txt changes
# TODO manage log groups
# TODO silence slacker
# TODO fill description with git commit, jenkins build or local info
# TODO wire to specific alias
# TODO retain only n versions

# creating docopt parameters and usage help
DOC = '''Usage:
        ramuda bundle
        ramuda deploy
        ramuda list
        ramuda metrics <lambda>
        ramuda wire
        ramuda unwire
        ramuda delete  -f <lambda>
        ramuda rollback  <lambda> [<version>]
        ramuda ping <lambda> [<version>]
        ramuda version

Options:
-h --help           show this
'''


def are_credentials_still_valid():
    """Wrapper to bail out on invalid credentials."""
    from gcdt.ramuda_utils import are_credentials_still_valid as acsv
    exit_code = acsv()
    if exit_code:
        sys.exit(1)


def get_user_config():
    slack_tocken, slack_channel = read_gcdt_user_config(compatibility_mode='kumo')
    if not slack_tocken:
        sys.exit(1)
    else:
        return slack_tocken, slack_channel


def main():
    exit_code = 0
    arguments = docopt(DOC)
    if arguments['version']:
        utils.version()
        sys.exit(0)

    context = get_context('ramuda', get_command(arguments))
    datadog_notification(context)

    if arguments['list']:
        are_credentials_still_valid()
        exit_code = list_functions()
        log.debug('debug_test')
        log.info('info_test')
    elif arguments['metrics']:
        are_credentials_still_valid()
        exit_code = get_metrics(arguments['<lambda>'])
    elif arguments['deploy']:
        are_credentials_still_valid()
        slack_token, slack_channel = get_user_config()
        conf = read_lambda_config()
        lambda_name = conf.get('lambda.name')
        lambda_description = conf.get('lambda.description')
        role_arn = conf.get('lambda.role')
        lambda_handler = conf.get('lambda.handlerFunction')
        handler_filename = conf.get('lambda.handlerFile')
        timeout = int(conf.get_string('lambda.timeout'))
        memory_size = int(conf.get_string('lambda.memorySize'))
        folders_from_file = conf.get('bundling.folders')
        subnet_ids = conf.get('lambda.vpc.subnetIds', None)
        security_groups = conf.get('lambda.vpc.securityGroups', None)
        artifact_bucket = conf.get('deployment.artifactBucket', None)
        exit_code = deploy_lambda(lambda_name, role_arn, handler_filename,
                                  lambda_handler, folders_from_file,
                                  lambda_description, timeout,
                                  memory_size, subnet_ids=subnet_ids,
                                  security_groups=security_groups,
                                  artifact_bucket=artifact_bucket)
    elif arguments['delete']:
        are_credentials_still_valid()
        slack_token, slack_channel = get_user_config()
        exit_code = delete_lambda(arguments['<lambda>'],
                                  slack_token=slack_token, slack_channel=slack_channel)
    elif arguments['wire']:
        are_credentials_still_valid()
        slack_token, slack_channel = get_user_config()
        conf = read_lambda_config()
        function_name = conf.get('lambda.name')
        s3_event_sources = conf.get('lambda.events.s3Sources', [])
        time_event_sources = conf.get('lambda.events.timeSchedules', [])
        exit_code = wire(function_name, s3_event_sources, time_event_sources,
                         slack_token=slack_token, slack_channel=slack_channel)
    elif arguments['unwire']:
        are_credentials_still_valid()
        slack_token, slack_channel = get_user_config()
        conf = read_lambda_config()
        function_name = conf.get('lambda.name')
        s3_event_sources = conf.get('lambda.events.s3Sources', [])
        time_event_sources = conf.get('lambda.events.timeSchedules', [])
        exit_code = unwire(function_name, s3_event_sources, time_event_sources,
                           slack_token=slack_token, slack_channel=slack_channel)
    elif arguments['bundle']:
        conf = read_lambda_config()
        handler_filename = conf.get('lambda.handlerFile')
        folders_from_file = conf.get('bundling.folders')
        exit_code = bundle_lambda(handler_filename, folders_from_file)
    elif arguments['rollback']:
        are_credentials_still_valid()
        slack_token, slack_channel = get_user_config()
        if arguments['<version>']:
            exit_code = rollback(arguments['<lambda>'], 'ACTIVE',
                                 arguments['<version>'],
                                 slack_token=slack_token, slack_channel=slack_channel)
        else:
            exit_code = rollback(arguments['<lambda>'], 'ACTIVE',
                                 slack_token=slack_token, slack_channel=slack_channel)
    elif arguments['ping']:
        are_credentials_still_valid()
        if arguments['<version>']:
            ping(arguments['<lambda>'], version=arguments['<version>'])
        else:
            ping(arguments['<lambda>'])

    if exit_code:
        datadog_error(context)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()