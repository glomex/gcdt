#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""ramuda.
Script to deploy Lambda functions to AWS
"""

from __future__ import unicode_literals, print_function
import sys

from clint.textui import colored

from . import utils
from .ramuda_core import list_functions, get_metrics, deploy_lambda, \
    wire, bundle_lambda, unwire, delete_lambda, rollback, ping, info, \
    cleanup_bundle, invoke
from .gcdt_cmd_dispatcher import cmd
from .gcdt_defaults import DEFAULT_CONFIG
from . import gcdt_lifecycle


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
        ramuda delete [-v] -f <lambda>
        ramuda rollback [-v] <lambda> [<version>]
        ramuda ping [-v] <lambda> [<version>]
        ramuda invoke [-v] <lambda> [<version>] [--invocation-type=<type>] --payload=<payload> [--outfile=<file>]
        ramuda version

Options:
-h --help               show this
-v --verbose            show debug messages
--keep                  keep (reuse) installed packages
--payload=payload       '{"foo": "bar"}' or file://input.txt
--invocation-type=type  Event, RequestResponse or DryRun
--outfile=file          write the response to file
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
        settings=settings
    )
    return exit_code


@cmd(spec=['metrics', '<lambda>'])
def metrics_cmd(lambda_name, **tooldata):
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    return get_metrics(awsclient, lambda_name)


@cmd(spec=['delete', '-f', '<lambda>'])
def delete_cmd(force, lambda_name, **tooldata):
    context = tooldata.get('context')
    config = tooldata.get('config')
    awsclient = context.get('_awsclient')
    function_name = config['lambda'].get('name', None)
    if function_name == str(lambda_name):
        s3_event_sources = config['lambda'].get('events', []).get('s3Sources', [])
        time_event_sources = config['lambda'].get('events', []).get('timeSchedules', [])
        exit_code = delete_lambda(awsclient, lambda_name,
                                  s3_event_sources,
                                  time_event_sources)
    else:
        exit_code = delete_lambda(
            awsclient, lambda_name, [], [])
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
    s3_event_sources = config['lambda'].get('events', []).get('s3Sources', [])
    time_event_sources = config['lambda'].get('events', []).get('timeSchedules', [])
    exit_code = wire(awsclient, function_name, s3_event_sources,
                     time_event_sources)
    return exit_code


@cmd(spec=['unwire'])
def unwire_cmd(**tooldata):
    context = tooldata.get('context')
    config = tooldata.get('config')
    awsclient = context.get('_awsclient')
    function_name = config['lambda'].get('name')
    s3_event_sources = config['lambda'].get('events', []).get('s3Sources', [])
    time_event_sources = config['lambda'].get('events', []).get('timeSchedules', [])
    exit_code = unwire(awsclient, function_name, s3_event_sources,
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
    #version = None
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    if version:
        response = ping(awsclient, lambda_name,
                        version=version)
    else:
        response = ping(awsclient, lambda_name)
    if 'alive' in str(response):
        print('Cool, your lambda function did respond to ping with %s.' %
              str(response))
    else:
        print(colored.red('Your lambda function did not respond to ping.'))
        return 1


@cmd(spec=['invoke', '<lambda>', '<version>', '--invocation-type', '--payload', '--outfile'])
def invoke_cmd(lambda_name, version, itype, payload, outfile, **tooldata):
    # samples
    # $ ramuda invoke infra-dev-sample-lambda-unittest --payload='{"ramuda_action": "ping"}'
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    invoke(awsclient, lambda_name, payload, invocation_type=itype, version=version, outfile=outfile)


def main():
    sys.exit(gcdt_lifecycle.main(DOC, 'ramuda',
                                 dispatch_only=['version', 'clean']))


if __name__ == '__main__':
    main()
