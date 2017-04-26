# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import mock

from gcdt.gcdt_plugins import load_plugins, get_plugin_versions
from gcdt.gcdt_signals import check_hook_mechanism_is_intact


def test_load_plugins():
    ep = mock.Mock(spec=['load'])
    plugin = mock.Mock(spec=['register', 'deregister'])
    ep.load.return_value = plugin

    with mock.patch('pkg_resources.iter_entry_points', return_value=[ep]):
        load_plugins()
        ep.load.assert_called_once()
        plugin.register.assert_called_once()


def test_check_hook_mechanism_is_intact():
    class _dummy(object):
        def register(self):
            pass

        def deregister(self):
            pass

    assert check_hook_mechanism_is_intact(_dummy) is True


def test_check_hook_mechanism_is_intact_detects_missing():
    class _dummy(object):
        def register(self):
            pass

    assert check_hook_mechanism_is_intact(_dummy) is False


def test_get_plugin_versions():
    # 'gcdt-bundler' and 'gcdt-lookups are dev requirements so this be fine
    versions = get_plugin_versions()
    assert 'gcdt-bundler' in versions
    assert 'gcdt-lookups' in versions
