#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""ramuda.
Commands to deploy Lambda functions to AWS
"""

from __future__ import unicode_literals, print_function

import sys

from clint.textui import colored

from . import gcdt_lifecycle
from . import utils
from .gcdt_cmd_dispatcher import cmd
from .gcdt_defaults import DEFAULT_CONFIG
from .ramuda_core import list_functions, get_metrics, deploy_lambda, \
    bundle_lambda, delete_lambda_deprecated, rollback,\
    ping, info, cleanup_bundle, invoke, logs, delete_lambda
from gcdt.ramuda_wire import wire, wire_deprecated, unwire, unwire_deprecated
from .ramuda_utils import check_and_format_logs_params
from .gcdt_logging import getLogger


log = getLogger(__name__)

# TODO introduce own config for account detection
# TODO re-upload on requirements.txt changes
# TODO manage log groups
# TODO fill description with git commit, jenkins build or local info
# TODO wire to specific alias
# TODO retain only n versions

# creating docopt parameters and usage help
DOC = '''Usage:
        ramuda clean
        ramuda bundle [--keep] [-v]
        ramuda deploy [--keep] [-v]
        ramuda list
        ramuda metrics <lambda>
        ramuda info
        ramuda wire [-v]
        ramuda unwire [-v]
        ramuda delete [-v] -f <lambda> [--delete-logs]
        ramuda rollback [-v] <lambda> [<version>]
        ramuda ping [-v] <lambda> [<version>]
        ramuda invoke [-v] <lambda> [<version>] [--invocation-type=<type>] --payload=<payload> [--outfile=<file>]
        ramuda logs <lambda> [--start=<start>] [--end=<end>] [--tail]
        ramuda version

Options:
-h --help               show this
-v --verbose            show debug messages
--keep                  keep (reuse) installed packages
--payload=payload       '{"foo": "bar"}' or file://input.txt
--invocation-type=type  Event, RequestResponse or DryRun
--outfile=file          write the response to file
--delete-logs           delete the log group and contained logs
--start=start           log start UTC '2017-06-28 14:23' or '1h', '3d', '5w', ...
--end=end               log end UTC '2017-06-28 14:25' or '2h', '4d', '6w', ...
--tail                  continuously output logs (can't use '--end'), stop 'Ctrl-C'
'''


@cmd(spec=['version'])
def version_cmd():
    utils.version()


@cmd(spec=['clean'])
def clean_cmd():
    return cleanup_bundle()


@cmd(spec=['list'])
def list_cmd(**tooldata):
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    return list_functions(awsclient)


@cmd(spec=['deploy', '--keep'])
def deploy_cmd(keep, **tooldata):
    context = tooldata.get('context')
    context['keep'] = keep or DEFAULT_CONFIG['ramuda']['keep']
    config = tooldata.get('config')
    awsclient = context.get('_awsclient')
    fail_deployment_on_unsuccessful_ping = \
        config.get('failDeploymentOnUnsuccessfulPing', False)
    lambda_name = config['lambda'].get('name')
    lambda_description = config['lambda'].get('description')
    role_arn = config['lambda'].get('role')
    lambda_handler = config['lambda'].get('handlerFunction')
    handler_filename = config['lambda'].get('handlerFile')
    timeout = int(config['lambda'].get('timeout'))
    memory_size = int(config['lambda'].get('memorySize'))
    folders_from_file = config['bundling'].get('folders')
    subnet_ids = config['lambda'].get('vpc', {}).get('subnetIds', None)
    security_groups = config['lambda'].get('vpc', {}).get('securityGroups', None)
    artifact_bucket = config.get('deployment', {}).get('artifactBucket', None)
    zipfile = context['_zipfile']
    runtime = config['lambda'].get('runtime', 'python2.7')
    environment = config['lambda'].get('environment', {})
    retention_in_days = config['lambda'].get('logs', {}).get('retentionInDays', None)
    if runtime:
        assert runtime in DEFAULT_CONFIG['ramuda']['runtime']
    settings = config['lambda'].get('settings', None)
    exit_code = deploy_lambda(
        awsclient, lambda_name, role_arn, handler_filename,
        lambda_handler, folders_from_file,
        lambda_description, timeout,
        memory_size, subnet_ids=subnet_ids,
        security_groups=security_groups,
        artifact_bucket=artifact_bucket,
        zipfile=zipfile,
        fail_deployment_on_unsuccessful_ping=
        fail_deployment_on_unsuccessful_ping,
        runtime=runtime,
        settings=settings,
        environment=environment,
        retention_in_days=retention_in_days
    )
    return exit_code


@cmd(spec=['metrics', '<lambda>'])
def metrics_cmd(lambda_name, **tooldata):
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    return get_metrics(awsclient, lambda_name)


@cmd(spec=['delete', '-f', '<lambda>', '--delete-logs'])
def delete_cmd(force, lambda_name, delete_logs, **tooldata):
    context = tooldata.get('context')
    config = tooldata.get('config')
    awsclient = context.get('_awsclient')
    function_name = config['lambda'].get('name', None)
    if function_name == str(lambda_name):
        if 'events' in config['lambda']:
            events = config['lambda']['events']
            if isinstance(events, list):
                exit_code = delete_lambda(awsclient, function_name, events, delete_logs)
            elif isinstance(events, dict):
                s3_event_sources = config['lambda'].get('events', []).get('s3Sources', [])
                time_event_sources = config['lambda'].get('events', []).get('timeSchedules', [])
                exit_code = delete_lambda_deprecated(awsclient, lambda_name,
                                                     s3_event_sources,
                                                     time_event_sources,
                                                     delete_logs)
    else:
        exit_code = delete_lambda(awsclient, function_name, [], delete_logs)
    return exit_code


@cmd(spec=['info'])
def info_cmd(**tooldata):
    context = tooldata.get('context')
    config = tooldata.get('config')
    awsclient = context.get('_awsclient')
    function_name = config['lambda'].get('name')
    s3_event_sources = config['lambda'].get('events', []).get('s3Sources', [])
    time_event_sources = config['lambda'].get('events', []).get('timeSchedules', [])
    return info(awsclient, function_name, s3_event_sources,
                time_event_sources)


@cmd(spec=['wire'])
def wire_cmd(**tooldata):
    context = tooldata.get('context')
    config = tooldata.get('config')
    awsclient = context.get('_awsclient')
    function_name = config['lambda'].get('name')
    if 'events' in config['lambda']:
        events = config['lambda']['events']
        if isinstance(events, list):
            exit_code = wire(awsclient, events, function_name)
        elif isinstance(events, dict):
            s3_event_sources = config['lambda'].get('events', []).get('s3Sources', [])
            time_event_sources = config['lambda'].get('events', []).get('timeSchedules', [])
            exit_code = wire_deprecated(awsclient, function_name, s3_event_sources,
                                        time_event_sources)
        return exit_code


@cmd(spec=['unwire'])
def unwire_cmd(**tooldata):
    context = tooldata.get('context')
    config = tooldata.get('config')
    awsclient = context.get('_awsclient')
    function_name = config['lambda'].get('name')
    if 'events' in config['lambda']:
        events = config['lambda']['events']
        if isinstance(events, list):
            exit_code = unwire(awsclient, events, function_name)
        elif isinstance(events, dict):
            s3_event_sources = config['lambda'].get('events', []).get('s3Sources', [])
            time_event_sources = config['lambda'].get('events', []).get('timeSchedules', [])
            exit_code = unwire_deprecated(awsclient, function_name, s3_event_sources,
                                          time_event_sources)
        return exit_code


@cmd(spec=['bundle', '--keep'])
def bundle_cmd(keep, **tooldata):
    context = tooldata.get('context')
    return bundle_lambda(context['_zipfile'])


@cmd(spec=['rollback', '<lambda>', '<version>'])
def rollback_cmd(lambda_name, version, **tooldata):
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    if version:
        exit_code = rollback(awsclient, lambda_name, 'ACTIVE',
                             version)
    else:
        exit_code = rollback(awsclient, lambda_name, 'ACTIVE')
    return exit_code


@cmd(spec=['ping', '<lambda>', '<version>'])
def ping_cmd(lambda_name, version=None, **tooldata):
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    if version:
        response = ping(awsclient, lambda_name,
                        version=version)
    else:
        response = ping(awsclient, lambda_name)
    if 'alive' in str(response):
        log.info('Cool, your lambda function did respond to ping with %s.' %
              str(response))
    else:
        log.info(colored.red('Your lambda function did not respond to ping.'))
        return 1


@cmd(spec=['invoke', '<lambda>', '<version>', '--invocation-type', '--payload', '--outfile'])
def invoke_cmd(lambda_name, version, itype, payload, outfile, **tooldata):
    # samples
    # $ ramuda invoke infra-dev-sample-lambda-unittest --payload='{"ramuda_action": "ping"}'
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    results = invoke(awsclient, lambda_name, payload, invocation_type=itype,
                     version=version, outfile=outfile)
    log.info('invoke result:')
    log.info(results)


@cmd(spec=['logs', '<lambda>', '--start', '--end', '--tail'])
def logs_cmd(lambda_name, start, end, tail, **tooldata):

    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    if tail and end:
        log.error(colored.red('You can not use \'--end\' and \'--tail\' options together.'))
        return 1

    start_dt, end_dt = check_and_format_logs_params(start, end, tail)

    if end and end_dt <= start_dt:
        log.error(colored.red('\'--end\' value before \'--start\' value.'))
        return 1

    if tail:
        log.info(colored.yellow('Use \'Ctrl-C\' to exit tail mode'))
    logs(awsclient, lambda_name, start_dt=start_dt, end_dt=end_dt, tail=tail)


def main():
    sys.exit(gcdt_lifecycle.main(DOC, 'ramuda',
                                 dispatch_only=['version', 'clean']))


if __name__ == '__main__':
    main()
