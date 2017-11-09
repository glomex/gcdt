# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import random
import string
import sys
import getpass
import subprocess
import time
from time import sleep
import collections
import json

import os
from clint.textui import prompt, colored
from tabulate import tabulate

from . import __version__
from .package_utils import get_package_versions
from .gcdt_plugins import get_plugin_versions
from .gcdt_logging import getLogger

PY3 = sys.version_info[0] >= 3

if PY3:
    basestring = str


log = getLogger(__name__)


def version():
    """Output version of gcdt tools and plugins."""
    log.info('gcdt version %s' % __version__)
    tools = get_plugin_versions('gcdttool10')
    if tools:
        log.info('gcdt tools:')
        for p, v in tools.items():
            log.info(' * %s version %s' % (p, v))
    log.info('gcdt plugins:')
    for p, v in get_plugin_versions().items():
        log.info(' * %s version %s' % (p, v))
    generators = get_plugin_versions('gcdtgen10')
    if generators:
        log.info('gcdt scaffolding generators:')
        for p, v in generators.items():
            log.info(' * %s version %s' % (p, v))


def retries(max_tries, delay=1, backoff=2, exceptions=(Exception,), hook=None):
    """Function decorator implementing retrying logic.

    delay: Sleep this many seconds * backoff * try number after failure
    backoff: Multiply delay by this factor after each failure
    exceptions: A tuple of exception classes; default (Exception,)
    hook: A function with the signature: (tries_remaining, exception, mydelay)
    """

    """
    def example_hook(tries_remaining, exception, delay):
        '''Example exception handler; prints a warning to stderr.

        tries_remaining: The number of tries remaining.
        exception: The exception instance which was raised.
        '''
        print >> sys.stderr, "Caught '%s', %d tries remaining, sleeping for %s seconds" % (exception, tries_remaining, delay)

    The decorator will call the function up to max_tries times if it raises
    an exception.

    By default it catches instances of the Exception class and subclasses.
    This will recover after all but the most fatal errors. You may specify a
    custom tuple of exception classes with the 'exceptions' argument; the
    function will only be retried if it raises one of the specified
    exceptions.

    Additionally you may specify a hook function which will be called prior
    to retrying with the number of remaining tries and the exception instance;
    see given example. This is primarily intended to give the opportunity to
    log the failure. Hook is not called after failure if no retries remain.
    """
    def dec(func):
        def f2(*args, **kwargs):
            mydelay = delay
            #tries = range(max_tries)
            #tries.reverse()
            tries = range(max_tries-1, -1, -1)
            for tries_remaining in tries:
                try:
                    return func(*args, **kwargs)
                except GracefulExit:
                    raise
                except exceptions as e:
                    if tries_remaining > 0:
                        if hook is not None:
                            hook(tries_remaining, e, mydelay)
                        sleep(mydelay)
                        mydelay *= backoff
                    else:
                        raise
        return f2
    return dec


def _get_user():
    return getpass.getuser()


def get_env():
    """
    Read environment from ENV and mangle it to a (lower case) representation
    Note: gcdt.utils get_env() is used in many cloudformation.py templates
    :return: Environment as lower case string (or None if not matched)
    """
    env = os.getenv('ENV', os.getenv('env', None))
    if env:
        env = env.lower()
    return env


def get_context(awsclient, env, tool, command, arguments=None):
    """This assembles the tool context. Private members are preceded by a '_'.

    :param tool:
    :param command:
    :return: dictionary containing the gcdt tool context
    """
    # TODO: elapsed, artifact(stack, depl-grp, lambda, api)
    if arguments is None:
        arguments = {}
    context = {
        '_awsclient': awsclient,
        'env': env,
        'tool': tool,
        'command': command,
        '_arguments': arguments,  # TODO clean up arguments -> args
        'version': __version__,
        'user': _get_user(),
        'plugins': get_plugin_versions().keys()
    }

    return context


def get_command(arguments):
    """Extract the first argument from arguments parsed by docopt.

    :param arguments parsed by docopt:
    :return: command
    """
    return [k for k, v in arguments.items()
            if not k.startswith('-') and v is True][0]


def execute_scripts(scripts):
    for script in scripts:
        exit_code = _execute_script(script)
        if exit_code != 0:
            return exit_code
    return 0


def _execute_script(file_name):
    if os.path.isfile(file_name):
        log.info('Executing %s ...' % file_name)
        exit_code = subprocess.call([file_name, '-e'])
        return exit_code
    else:
        log.warn('No file found matching %s...' % file_name)
        return 1


def check_gcdt_update():
    """Check whether a newer gcdt is available and output a warning.

    """
    try:
        inst_version, latest_version = get_package_versions('gcdt')
        if inst_version < latest_version:
            log.warn('Please consider an update to gcdt version: %s' %
                                 latest_version)
    except GracefulExit:
        raise
    except Exception:
        log.warn('PyPi appears to be down - we currently can\'t check for newer gcdt versions')


# adapted from:
# http://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge/7205107#7205107
def dict_selective_merge(a, b, selection, path=None):
    """Conditionally merges b into a if b's keys are contained in selection

    :param a:
    :param b:
    :param selection: limit merge to these top-level keys
    :param path:
    :return:
    """
    if path is None:
        path = []
    for key in b:
        if key in selection:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    dict_selective_merge(a[key], b[key], b[key].keys(), path + [str(key)])
                elif a[key] != b[key]:
                    # update the value
                    a[key] = b[key]
            else:
                a[key] = b[key]
    return a


def dict_merge(a, b, path=None):
    """merges b into a"""
    return dict_selective_merge(a, b, b.keys(), path)


# TODO test this properly!
# TODO use logging
# TODO move to gcdt-checks!
def are_credentials_still_valid(awsclient):
    """Check whether the credentials have expired.

    :param awsclient:
    :return: exit_code
    """
    client = awsclient.get_client('lambda')
    try:
        client.list_functions()
    except GracefulExit:
        raise
    except Exception as e:
        log.debug(e)
        log.error(e)
        return 1
    return 0


# http://code.activestate.com/recipes/578948-flattening-an-arbitrarily-nested-list-in-python/
def flatten(lis):
    """Given a list, possibly nested to any level, return it flattened."""
    new_lis = []
    for item in lis:
        if isinstance(item, collections.Sequence) and not isinstance(item, basestring):
            new_lis.extend(flatten(item))
        else:
            new_lis.append(item)
    return new_lis


class GracefulExit(Exception):
    """
    transport the signal information
    note: if you capture Exception you have to deal with this case, too
    """
    pass


def signal_handler(signum, frame):
    """
    handle signals.
    example: 'signal.signal(signal.SIGTERM, signal_handler)'
    """
    # signals are CONSTANTS so there is no mapping from signum to description
    # so please add to the mapping in case you use more signals!
    description = '%d' % signum
    if signum == 2:
        description = 'SIGINT'
    elif signum == 15:
        description = 'SIGTERM'
    raise GracefulExit(description)


def json2table(json):
    """This does format a dictionary into a table.
    Note this expects a dictionary (not a json string!)

    :param json:
    :return:
    """
    filter_terms = ['ResponseMetadata']
    table = []
    try:
        for k in filter(lambda k: k not in filter_terms, json.keys()):
            table.append([k.encode('ascii', 'ignore'),
                         str(json[k]).encode('ascii', 'ignore')])
        return tabulate(table, tablefmt='fancy_grid')
    except GracefulExit:
        raise
    except Exception as e:
        log.error(e)
        return json


def fix_old_kumo_config(config, silent=False):
    # DEPRECATED since 0.1.420
    if config.get('kumo', {}).get('cloudformation', {}):
        if not silent:
            log.warn('kumo config contains a deprecated "cloudformation" section!')
        cloudformation = config['kumo'].pop('cloudformation')
        stack = {}
        for key in cloudformation.keys():
            if key in ['StackName', 'TemplateBody', 'artifactBucket', 'RoleARN']:
                stack[key] = cloudformation.pop(key)
        if stack:
            config['kumo']['stack'] = stack
        if cloudformation:
            config['kumo']['parameters'] = cloudformation
        if not silent:
            log.warn('Your kumo config should look like this:')
            log.warn(json.dumps(config['kumo']))
    return config


def random_string(length=6):
    """Create a random 6 character string.

    note: in case you use this function in a test during test together with
    an awsclient then this function is altered so you get reproducible results
    that will work with your recorded placebo json files (see helpers_aws.py).
    """
    return ''.join([random.choice(string.ascii_lowercase) for i in range(length)])


def time_now():
    """Like int(time.time() * 1000) but supports record and playback for testing.

    note: in case you use this function in a test during test together with
    an awsclient then this function is altered so you get reproducible results
    that will work with your recorded placebo json files (see helpers_aws.py).
    """
    return int(time.time()) * 1000


def all_pages(method, request, accessor, cond=None):
    """Helper to process all pages using botocore service methods (exhausts NextToken).
    note: `cond` is optional... you can use it to make filtering more explicit
    if you like. Alternatively you can do the filtering in the `accessor` which
    is perfectly fine, too
    Note: lambda uses a slightly different mechanism so there is a specific version in
    ramuda_utils.

    :param method: service method
    :param request: request dictionary for service call
    :param accessor: function to extract data from each response
    :param cond: filter function to return True / False based on a response
    :return: list of collected resources
    """
    if cond is None:
        cond = lambda x: True
    result = []
    next_token = None
    while True:
        if next_token:
            request['nextToken'] = next_token
        response = method(**request)
        if cond(response):
            data = accessor(response)
            if data:
                if isinstance(data, list):
                    result.extend(data)
                else:
                    result.append(data)
        if 'nextToken' not in response:
            break
        next_token = response['nextToken']

    return result