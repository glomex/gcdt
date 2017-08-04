# -*- coding: utf-8 -*-
"""config_reader reads a config in json format.
"""
from __future__ import unicode_literals, print_function
import json


# TODO implement config_reader for 'gcdt_<env>.json' as plugin!!


def read_json_config(config_file):
    # currently this is only a helper for test
    with open(config_file) as jfile:
        data = json.load(jfile)
    return data
