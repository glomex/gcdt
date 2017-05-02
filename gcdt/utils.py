# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import sys
import getpass
import subprocess
from time import sleep
import collections

import os
from clint.textui import prompt, colored

from . import __version__
from .package_utils import get_package_versions
from .gcdt_plugins import get_plugin_versions
from .gcdt_logging import getLogger

PY3 = sys.version_info[0] >= 3

if PY3:
    basestring = str


log = getLogger(__name__)


def version():
    """Print version of gcdt tools and plugins."""
    print('gcdt version %s' % __version__)
    print('gcdt plugins:')
    for p, v in get_plugin_versions().items():
        print(' * %s version %s' % (p, v))
    generators = get_plugin_versions('gcdtgen10')
    if generators:
        print('gcdt scaffolding generators:')
        for p, v in generators.items():
            print(' * %s version %s' % (p, v))


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


# TODO check if this is used and move to hocon config reader
'''
def read_gcdt_user_config_value(key, default=None, gcdt_file=None):
    """Read .gcdt config file from user home and return value for key.
    Configuration keys are in the form <command>.<key>

    :return: value if present, or default
    """
    extension = 'gcdt'
    if not gcdt_file:
        gcdt_file = os.path.expanduser('~') + '/.' + extension
    try:
        config = ConfigFactory.parse_file(gcdt_file)
        value = config.get(key)
    except Exception:
        value = default
    return value
'''


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
    #return [k for k, v in arguments.iteritems()
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
        print('Executing %s ...' % file_name)
        exit_code = subprocess.call([file_name, '-e'])
        return exit_code
    else:
        print('No file found matching %s...' % file_name)
        return 1


def check_gcdt_update():
    """Check whether a newer gcdt is available and output a warning.

    """
    inst_version, latest_version = get_package_versions('gcdt')
    if inst_version < latest_version:
        print(colored.yellow('Please consider an update to gcdt version: %s' %
                             latest_version))


# adapted from:
# http://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge/7205107#7205107
def dict_merge(a, b, path=None):
    """merges b into a"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key], path + [str(key)])
            elif a[key] != b[key]:
                # update the value
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


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
    except Exception as e:
        log.debug(e)
        print(e)
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
