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
    'reposerver': 'https://reposerver-prod-eu-west-1.infra.glomex.cloud/pypi/packages',
    'ramuda': {
        'settings_file': 'settings.json'
    }
}


# note this config is used in the config_reader to "overlay" the
# gcdt_defaults of gcdt.
CONFIG_READER_CONFIG = {
    'lookups': ['secret', 'ssl', 'stack', 'baseami'],
    'plugins': {
        'datadog_integration': {
            'datadog_api_key': 'lookup:secret:datadog.api_key'
        },
        'slack_integration': {
            'slack_webhook': 'http://localhost/'
        },
        'glomex_lookups': {
            'ami_accountid': '569909643510'
        }
    }
}
