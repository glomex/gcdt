# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import json
import os
from logging import getLogger
import importlib
from os import listdir

from bravado_core.spec import Spec
from bravado_core.validate import validate_object
from jsonschema.exceptions import ValidationError
from jsonschema import _utils
import pprint

import pytest

from . import here

# note: does nothing if the config samples are missing...
# this is a local debug tool (e.g. required gcdt packages are missing on Jenkins)
# query all json files from CONFIG_SAMPLE_PATH folder
CONFIG_SAMPLE_PATH = here('resources/glomex_config_samples')
CONFIGFILES = []
if os.path.exists(CONFIG_SAMPLE_PATH):
    CONFIGFILES = [f for f in listdir(CONFIG_SAMPLE_PATH) if f.endswith('.json')]


TOOLS = ['gcdt_kumo', 'gcdt_tenkai', 'gcdt_ramuda', 'gcdt_yugen',
         'gcdt_lookups', 'gcdt_slack_integration', 'gcdt_datadog_integration']


@pytest.fixture(params=TOOLS)
def gcdt_tool_package(request):
    return importlib.import_module(request.param)


@pytest.mark.parametrize('configfile', CONFIGFILES)
def test_gcdt_tool_spec(configfile, gcdt_tool_package):
    log = getLogger()
    with open(os.path.join(CONFIG_SAMPLE_PATH, configfile), 'r') as jfile:
        config = json.load(jfile)

    raw_spec = gcdt_tool_package.read_openapi()
    spec = Spec.from_dict(raw_spec, config={'use_models': True})

    top = raw_spec['definitions']['top']

    try:
        validate_object(spec, top, config)
    except ValidationError as e:
        # details
        # http://python-jsonschema.readthedocs.io/en/latest/errors/
        log.error('Config validation failed for %s',
                  _utils.format_as_index(e.relative_path))
        log.error(e.message)
        pinstance = pprint.pformat(e.instance, width=72)
        log.error('affected config section:')
        log.error(pinstance)
        pytest.fail(e.message)
