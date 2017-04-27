# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

"""This file contains configuration for gcdt tools so we do not need
hardcoded values.
"""

# basic structure:
'''
{
    'kumo': {},
    'tenkai': {},
    'ramuda': {},
    'yugen': {},
    'plugins': {
        '<plugin_name>': {}
    }
}
'''


DEFAULT_CONFIG = {
    'ramuda': {
        'settings_file': 'settings.json',
        'runtime': ['python2.7', 'nodejs4.3']
    }
}


# note this config is used in the config_reader to "overlay" the
# gcdt_defaults of gcdt.
CONFIG_READER_CONFIG = {
    'lookups': ['secret', 'ssl', 'stack', 'baseami'],
    'plugins': {
        'gcdt_datadog_integration': {
            'datadog_api_key': 'lookup:secret:datadog.api_key'
        },
        'gcdt_slack_integration': {
            'slack_webhook': 'lookup:secret:slack.webhook:CONTINUE_IF_NOT_FOUND'
        },
        'gcdt_lookups': {
            'ami_accountid': '569909643510'
        }
    }
}
