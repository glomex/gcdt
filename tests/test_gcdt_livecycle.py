# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import textwrap

import pytest
import mock

from gcdt.gcdt_lifecycle import main, lifecycle, _load_hooks
from gcdt.kumo_main import DOC
from gcdt import gcdt_signals
from gcdt_testtools.helpers import create_tempfile


@mock.patch('gcdt.gcdt_lifecycle.AWSClient', return_value='my_awsclient')
@mock.patch('gcdt.gcdt_lifecycle.docopt')
@mock.patch('gcdt.gcdt_lifecycle.lifecycle')
def test_main(mocked_lifecycle, mocked_docopt, mocked_awsclient):
    mocked_docopt.return_value = {
        u'--override-stack-policy': False,
        u'-f': False,
        u'delete': False,
        u'deploy': True,
        u'dot': False,
        u'generate': False,
        u'list': False,
        u'preview': False,
        u'version': False
    }
    main(DOC, 'kumo')
    # mocked_check_gcdt_update.assert_called_once()
    mocked_lifecycle.assert_called_once_with(
        'my_awsclient', 'dev', 'kumo', 'deploy',
        {'-f': False, '--override-stack-policy': False, 'version': False,
         'deploy': True, 'preview': False, 'list': False, 'generate': False,
         'dot': False, 'delete': False})


@mock.patch('gcdt.gcdt_lifecycle.cmd.dispatch')
@mock.patch('gcdt.gcdt_lifecycle.check_gcdt_update')
@mock.patch('gcdt.gcdt_lifecycle.docopt')
def test_main_dispatch_only(mocked_docopt, mocked_check_gcdt_update,
                            mocked_cmd_dispatch):
    mocked_docopt.return_value = {
        u'--override-stack-policy': False,
        u'-f': False,
        u'delete': False,
        u'deploy': False,
        u'dot': False,
        u'generate': False,
        u'list': False,
        u'preview': False,
        u'version': True
    }
    main(DOC, 'kumo')
    mocked_check_gcdt_update.assert_called_once()
    mocked_cmd_dispatch.assert_called_once_with(
        {'-f': False, '--override-stack-policy': False, 'version': True,
         'deploy': False, 'preview': False, 'list': False, 'generate': False,
         'dot': False, 'delete': False})


def _dummy_signal_factory(name, exp_signals):
    def _dummy_signal_handler(args):
        print('signal fired: %s' % name)
        if name == 'config_read_init':
            args[0]['foo'] = 'bar'
            args[0]['tool'] = 'kumo'
            args[1]['kumo'] = {}
        n = exp_signals.pop(0)
        assert n == name
    return _dummy_signal_handler


@mock.patch('gcdt.gcdt_lifecycle.cmd.dispatch', return_value=0)
@mock.patch('gcdt.gcdt_lifecycle.are_credentials_still_valid', return_value=False)
@mock.patch('gcdt.gcdt_lifecycle.check_gcdt_update')
@mock.patch('gcdt.gcdt_lifecycle.load_plugins')
def test_lifecycle(mocked_load_plugins, mocked_check_gcdt_update,
                   mocked_are_credentials_still_valid,
                   mocked_cmd_dispatch):
    # preparation
    signal_handlers = []  # GC cleans them up if there is no ref
    exp_signals = [
        'initialized',
        'config_read_init', 'config_read_finalized',
        'lookup_init', 'lookup_finalized',
        'config_validation_init', 'config_validation_finalized',
        'bundle_pre', 'bundle_init', 'bundle_finalized',
        'command_init', 'command_finalized',
        'finalized'
    ]
    for s in exp_signals:
        sig = gcdt_signals.__dict__[s]
        handler = _dummy_signal_factory(s, exp_signals)
        sig.connect(handler)
        signal_handlers.append(handler)

    # livecycle execution
    arguments = {
        u'--override-stack-policy': True,
        u'-f': False,
        u'delete': False,
        u'deploy': True,
        u'dot': False,
        u'generate': False,
        u'list': False,
        u'preview': False,
        u'version': False
    }
    exit_code = lifecycle('my_awsclient', 'dev', 'kumo', 'deploy', arguments)
    assert exit_code == 0
    assert exp_signals == []

    mocked_load_plugins.assert_called_once()
    mocked_check_gcdt_update.assert_called_once()
    mocked_are_credentials_still_valid.called_once_with('my_awsclient')
    mocked_cmd_dispatch.called_once_with('my_awsclient')


@mock.patch('gcdt.gcdt_lifecycle.cmd.dispatch', side_effect=Exception)
@mock.patch('gcdt.gcdt_lifecycle.are_credentials_still_valid', return_value=False)
@mock.patch('gcdt.gcdt_lifecycle.check_gcdt_update')
@mock.patch('gcdt.gcdt_lifecycle.load_plugins')
def test_lifecycle_error(mocked_load_plugins, mocked_check_gcdt_update,
                   mocked_are_credentials_still_valid,
                   mocked_cmd_dispatch):
    # preparation
    signal_handlers = []  # GC cleans them up if there is no ref
    exp_signals = [
        'initialized',
        'config_read_init', 'config_read_finalized',
        'lookup_init', 'lookup_finalized',
        'config_validation_init', 'config_validation_finalized',
        'bundle_pre', 'bundle_init', 'bundle_finalized',
        'command_init',
        'error'
    ]
    for s in exp_signals:
        sig = gcdt_signals.__dict__[s]
        handler = _dummy_signal_factory(s, exp_signals)
        sig.connect(handler)
        signal_handlers.append(handler)

    # livecycle execution
    arguments = {
        u'--override-stack-policy': True,
        u'-f': False,
        u'delete': False,
        u'deploy': True,
        u'dot': False,
        u'generate': False,
        u'list': False,
        u'preview': False,
        u'version': False
    }
    exit_code = lifecycle('my_awsclient', 'dev', 'kumo', 'deploy', arguments)
    assert exit_code == 1
    assert exp_signals == []

    mocked_load_plugins.assert_called_once()
    mocked_check_gcdt_update.assert_called_once()
    mocked_are_credentials_still_valid.called_once_with('my_awsclient')
    mocked_cmd_dispatch.called_once_with('my_awsclient')


def test_load_hooks():
    tfile = create_tempfile(textwrap.dedent("""
    COUNT = {'register': 0, 'deregister': 0}

    def register():
        COUNT['register'] += 1


    def deregister():
        COUNT['deregister'] += 1
    """))
    module = _load_hooks(tfile)

    assert module.COUNT['register'] == 1
    os.unlink(tfile)
