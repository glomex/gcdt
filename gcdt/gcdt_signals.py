# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from blinker import signal

# lifecycle implementation adapted from
# https://github.com/finklabs/aws-deploy/blob/master/aws_deploy/signals.py
# we use signals here for testability and better composition of code
# the signals provide hooks to add components into the tool lifecycle

# run-level signals:


initialized = signal('initialized')  # after reading arguments and context

config_read_init = signal('config_read_init')
config_read_finalized = signal('config_read_finalized')

check_credentials_init = signal('check_credentials_init')
check_credentials_finalized = signal('check_credentials_finalized')

lookup_init = signal('lookup_init')
lookup_finalized = signal('lookup_finalized')

config_validation_init = signal('config_validation_init')
config_validation_finalized = signal('config_validation_finalized')

bundle_pre = signal('bundle_pre')  # we need this signal to implement the prebundle-hook
bundle_init = signal('bundle_init')
bundle_finalized = signal('bundle_finalized')

command_init = signal('command_init')
command_finalized = signal('command_finalized')

error = signal('error')

finalized = signal('finalized')  # right before exit


def check_register_present(module):
    """Check for register method in module.

    :param module:
    :return: True if present.
    """
    if hasattr(module, 'register'):
        return True


def check_deregister_present(module):
    """Check for deregister method in module.

    :param module:
    :return: True if present.
    """
    if hasattr(module, 'deregister'):
        return True


def check_hook_mechanism_is_intact(module):
    """Check if the hook configuration is absent or has both register AND deregister.

    :param module:
    :return: True if valid plugin / module.
    """
    result = True
    if check_register_present(module):
        result = not result
    if check_deregister_present(module):
        result = not result
    return result
