# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import logging

import pkg_resources

from gcdt.gcdt_signals import check_hook_mechanism_is_intact, \
    check_register_present

log = logging.getLogger(__name__)


# TODO we have all plugins in one single repo so we need a mechanism to filter
# the ones we want to use!


def load_plugins(group='gcdt10'):
    """Load and register installed gcdt plugins.
    """
    # on using entrypoints:
    # http://stackoverflow.com/questions/774824/explain-python-entry-points
    # TODO: make sure we do not have conflicting generators installed!
    for ep in pkg_resources.iter_entry_points(group, name=None):
        plugin = ep.load()  # load the plugin
        if check_hook_mechanism_is_intact(plugin):
            if check_register_present(plugin):
                plugin.register()   # register the plugin so it listens to gcdt_signals
        else:
            log.warning('No valid hook configuration: %s. Not using hooks!', plugin)


def get_plugin_versions(group='gcdt10'):
    """Load and register installed gcdt plugins.
    """
    versions = {}
    for ep in pkg_resources.iter_entry_points(group, name=None):
        versions[ep.dist.project_name] = ep.dist.version

    return versions
