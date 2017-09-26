# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import imp
import logging
import signal
import sys
import json
from logging.config import dictConfig

import botocore.session
from docopt import docopt

from .utils import signal_handler
from gcdt.gcdt_exceptions import GracefulExit
from . import gcdt_signals
from .gcdt_awsclient import AWSClient
from .gcdt_cmd_dispatcher import cmd, get_command
from .gcdt_logging import logging_config
from .gcdt_plugins import load_plugins
from .gcdt_signals import check_hook_mechanism_is_intact, \
    check_register_present
from .gcdt_exceptions import GcdtError, InvalidCredentialsError
from .utils import get_context, check_gcdt_update, are_credentials_still_valid, \
    get_env

log = logging.getLogger(__name__)


def _load_hooks(path):
    """Load hook module and register signals.

    :param path: Absolute or relative path to module.
    :return: module
    """
    module = imp.load_source(os.path.splitext(os.path.basename(path))[0], path)
    if not check_hook_mechanism_is_intact(module):
        # no hooks - do nothing
        log.debug('No valid hook configuration: \'%s\'. Not using hooks!', path)
    else:
        if check_register_present(module):
            # register the template hooks so they listen to gcdt_signals
            module.register()
    return module


# lifecycle implementation adapted from
# https://github.com/finklabs/aws-deploy/blob/master/aws_deploy/tool.py
def lifecycle(awsclient, env, tool, command, arguments):
    """Tool lifecycle which provides hooks into the different stages of the
    command execution. See signals for hook details.
    """
    # TODO: remove all these lines
    #         log.error(context['error'])

    log.debug('### init')
    load_plugins()
    load_plugins('gcdttool10')
    context = get_context(awsclient, env, tool, command, arguments)

    # every tool needs a awsclient so we provide this via the context
    context['_awsclient'] = awsclient
    log.debug('### context:')
    log.debug(context)

    # config is "assembled" by config_reader NOT here!
    config = {}

    try:
        ## initialized
        gcdt_signals.initialized.send(context)
        log.debug('### initialized')
        check_gcdt_update()

        gcdt_signals.config_read_init.send((context, config))
        log.debug('### config_read_init')
        gcdt_signals.config_read_finalized.send((context, config))
        log.debug('### config_read_finalized')

        # register lifecycle hooks
        if os.path.exists('cloudformation.py'):
            # TODO tried to move this to gcdt-kumo but found no good solutino so far
            _load_hooks('cloudformation.py')  # register cloudformation.py hooks
        if 'hookfile' in config:
            _load_hooks(config['hookfile'])  # load hooks from hookfile

        # check_credentials
        gcdt_signals.check_credentials_init.send((context, config))
        log.debug('### check_credentials_init')
        gcdt_signals.check_credentials_finalized.send((context, config))
        log.debug('### check_credentials_finalized')

        ## lookup
        gcdt_signals.lookup_init.send((context, config))
        log.debug('### lookup_init')
        gcdt_signals.lookup_finalized.send((context, config))
        log.debug('### lookup_finalized')
        log.debug('### config after lookup:')
        log.debug(json.dumps(config))

        ## config validation
        gcdt_signals.config_validation_init.send((context, config))
        log.debug('### config_validation_init')
        gcdt_signals.config_validation_finalized.send((context, config))
        log.debug('### config_validation_finalized')

        ## check credentials are valid (AWS services)
        # DEPRECATED, use gcdt-awsume plugin instead
        # TODO use context expiration
        if are_credentials_still_valid(awsclient):
            raise InvalidCredentialsError()

        ## bundle step
        gcdt_signals.bundle_pre.send((context, config))
        log.debug('### bundle_pre')
        gcdt_signals.bundle_init.send((context, config))
        log.debug('### bundle_init')
        gcdt_signals.bundle_finalized.send((context, config))
        log.debug('### bundle_finalized')

        ## dispatch command (providing context and config => tooldata )
        gcdt_signals.command_init.send((context, config))
        log.debug('### command_init')

        if tool == 'gcdt':
            conf = config  # gcdt works on the whole config
        else:
            # other tools work on tool specific config
            conf = config.get(tool, None)
            if conf is None:
                raise GcdtError('config missing for \'%s\', bailing out!' % tool)
            conf = config.get(tool, {})
        exit_code = cmd.dispatch(arguments, context=context, config=conf)
        if exit_code:
            raise GcdtError('Error during execution of \'\' \'\'', tool, command)

        gcdt_signals.command_finalized.send((context, config))
        log.debug('### command_finalized')
    except GracefulExit:
        raise
    except Exception as e:
        log.exception(e)
        log.debug(str(e), exc_info=True)  # this adds the traceback
        context['error'] = str(e)
        gcdt_signals.error.send((context, config))
        log.debug('### error')
        return 1

    # TODO reporting (in case you want to get a summary / output to the user)

    gcdt_signals.finalized.send(context)
    log.debug('### finalized')
    return 0


def main(doc, tool, dispatch_only=None):
    """gcdt tools parametrized main function to initiate gcdt lifecycle.

    :param doc: docopt string
    :param tool: gcdt tool (gcdt, kumo, tenkai, ramuda, yugen)
    :param dispatch_only: list of commands which do not use gcdt lifecycle
    :return: exit_code
    """
    # Use signal handler to throw exception which can be caught to allow
    # graceful exit.
    # here: https://stackoverflow.com/questions/26414704/how-does-a-python-process-exit-gracefully-after-receiving-sigterm-while-waiting
    signal.signal(signal.SIGTERM, signal_handler)  # Jenkins
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl-C

    try:
        arguments = docopt(doc, sys.argv[1:])
        command = get_command(arguments)
        # DEBUG mode (if requested)
        verbose = arguments.pop('--verbose', False)
        if verbose:
            logging_config['loggers']['gcdt']['level'] = 'DEBUG'
        dictConfig(logging_config)

        if dispatch_only is None:
            dispatch_only = ['version']
        # assert on tool does not make sense any more!
        #assert tool in ['gcdt', 'kumo', 'tenkai', 'ramuda', 'yugen']

        if command in dispatch_only:
            # handle commands that do not need a lifecycle
            # Note: `dispatch_only` commands do not have a check for ENV variable!
            check_gcdt_update()
            return cmd.dispatch(arguments)
        else:
            env = get_env()
            if not env:
                log.error('\'ENV\' environment variable not set!')
                return 1

            awsclient = AWSClient(botocore.session.get_session())
            return lifecycle(awsclient, env, tool, command, arguments)
    except GracefulExit as e:
        log.info('Received %s signal - exiting command \'%s %s\'',
                 str(e), tool, command)
        return 1
