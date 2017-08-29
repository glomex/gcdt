# -*- coding: utf-8 -*-
"""tools to use openapi spec (validation, documentation, default, scaffolding)
"""
from __future__ import unicode_literals, print_function
import datetime
from copy import deepcopy
import logging
import re
import six
import textwrap
from collections import OrderedDict

import ruamel.yaml as yaml
from bravado_core.spec import Spec
from bravado_core.validate import validate_object
from jsonschema.exceptions import ValidationError
from jsonschema import _utils
import pprint

from .gcdt_logging import getLogger
from .utils import dict_merge, get_plugin_defaults
from . import GcdtError

try:
    from StringIO import StringIO
except ImportError:  # Python 3
    from io import StringIO


log = getLogger(__name__)


def read_openapi_ordered(openapi, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    """Load spec from yaml file.

    :return: dict containing spec
    """
    class OrderedLoader(Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    with open(openapi, 'r') as ofile:
        return yaml.load(ofile, OrderedLoader)


def validate_tool_config(raw_spec, config):
    """Helper to validate

    :param raw_spec:
    :param config:
    :return:
    """
    spec = Spec.from_dict(raw_spec, config={'use_models': True})

    top = raw_spec['definitions']['top']

    try:
        validate_object(spec, top, config)
    except ValidationError as e:
        # details
        # http://python-jsonschema.readthedocs.io/en/latest/errors/
        #log.error(e.message)
        pschema = pprint.pformat(e.schema, width=72)
        pinstance = pprint.pformat(e.instance, width=72)
        log.error(textwrap.dedent("""
            Failed validating %r in schema%s:
            %s
    
            On instance%s:
            %s
            """.rstrip()) % (
            e.validator,
            _utils.format_as_index(list(e.relative_schema_path)[:-1]),
            _utils.indent(pschema),
            _utils.format_as_index(e.relative_path),
            _utils.indent(pinstance),
        ))
        return e.message


# tools to generate data from openapi spec:
#  * default configuration (required properties that have defaults)
#  * min sample (only required properties)
#  * max sample (all properties)

# implementation started with codebase from:
# https://github.com/Trax-air/swagger-parser/blob/master/swagger_parser/swagger_parser.py
# (MIT) version 11th Jun 2017, 8534150

# why not keep the class structure of swagger-parser which implemented caching
# to speed things up??
# since we have different modes for scaffolding we can not have an example
# cache any more meaning a referenced definition can have different examples
# and defaults on different levels (one time it is required and has a default,
# another time this is not the case). therefor we need to fully evaluate the
# whole structure and can not reuse examples.

# note: there is a little section in the developer docs on incepting and
# validating config
def incept_defaults_helper(params, openapi, tool, is_plugin=False):
    """incept defaults where needed (after config is read from file).

    :param params: context, config (context - the _awsclient, etc..
                   config - The stack details, etc..)
    :param openapi: openapi spec in dict form
    :param tool: actual tool / plugin to incept defaults
    :param is_plugin: False (by default)
    :return:
    """
    log.debug('incepting defaults for \'%s\'.', tool)
    context, config = params

    if is_plugin:
        defaults = get_openapi_defaults(openapi, tool)
        if defaults:
            config_from_reader = deepcopy(config)
            dict_merge(config, {'plugins': {tool: defaults}})
            dict_merge(config, config_from_reader)
    else:
        is_config_from_reader = tool in config
        log.debug('config_from_reader: %s', is_config_from_reader)
        defaults = get_openapi_defaults(openapi, tool)
        #log.debug('defaults: %s', defaults)
        #log.debug('non_config_command in defaults: %s', defaults.get('non_config_commands', []))
        is_actual_non_config_command = (context['tool'] == tool and context['command'] in
            defaults.get('defaults', {}).get('non_config_commands', [])
        )
        log.debug('actual_non_config_command: %s', is_actual_non_config_command)
        if not is_config_from_reader and not is_actual_non_config_command:
            return
        if defaults:
            config_read_from_reader = deepcopy(config)
            if is_config_from_reader:
                dict_merge(config, {tool: defaults})
            elif is_actual_non_config_command:
                defaults['defaults']['validate'] = False  # disable config validation
                # incept only 'defaults' section
                dict_merge(config, {tool: {'defaults': defaults['defaults']}})

            dict_merge(config, config_read_from_reader)


def validate_config_helper(params, openapi, tool, is_plugin=False):
    """validate the config after lookups.
    :param params: context, config (context - the _awsclient, etc..
                   config - The stack details, etc..)
    :param is_plugin: False (by default)
    """
    log.debug('validating config for \'%s\'.', tool)
    context, config = params

    if is_plugin:
        defaults = get_plugin_defaults(config, tool)
        validation_switched_on = defaults.get('validate', True)
    else:
        validation_switched_on = config.get(tool, {}).get('defaults', {}).get('validate', True)

    if validation_switched_on:
        error = validate_tool_config(openapi, config)
        if error:
            context['error'] = error


def get_openapi_defaults(specification, def_name):
    """Get default configuration for the given definition.

    :param def_name: Name of the definition.
    :return: default config
    """
    return _build_one_definition_example(specification, def_name, 'default')


def get_openapi_scaffold_min(specification, def_name):
    """Get minimal configuration for the given definition (required properties).

    :param def_name: Name of the definition.
    :return: minimal config
    """
    return _build_one_definition_example(specification, def_name, 'sample-min')


def get_openapi_scaffold_max(specification, def_name):
    """Get maximal configuration for the given definition (all properties).

    :param def_name: Name of the definition.
    :return: maximal config
    """
    return _build_one_definition_example(specification, def_name, 'sample-max')


def _build_one_definition_example(specification, def_name, mode):
    # internal helper to create a sample from an openapi spec
    assert mode in ['default', 'sample-min', 'sample-max']

    if def_name not in specification['definitions'].keys():  # Def does not exist
        return None

    definitions_example = {}
    def_spec = specification['definitions'][def_name]

    if def_spec.get('type') == 'array' and 'items' in def_spec:
        item = _get_example_from_prop_spec(specification, def_spec['items'], mode)
        definitions_example[def_name] = [item]
        return definitions_example

    if 'properties' not in def_spec:
        example = _get_example_from_prop_spec(specification, def_spec, mode)
        #definitions_example[def_name] = example
        #return definitions_example
        return example

    # Get properties example value
    for prop_name, prop_spec in def_spec['properties'].items():
        required = prop_name in def_spec.get('required', [])
        if mode == 'sample-max' or required:
            example = _get_example_from_prop_spec(specification, prop_spec, mode)
            if example is None:
                continue
            definitions_example[prop_name] = example
    return definitions_example


def _check_type(value, type_def):
    """Check if the value is in the type given in type_def.

    Args:
        value: the var to test.
        type_def: string representing the type in swagger.

    Returns:
        True if the type is correct, False otherwise.
    """
    if type_def == 'integer':
        try:
            # We accept string with integer ex: '123'
            int(value)
            return True
        except ValueError:
            return isinstance(value, six.integer_types) and not isinstance(value, bool)
    elif type_def == 'number':
        return isinstance(value, (six.integer_types, float)) and not isinstance(value, bool)
    elif type_def == 'string':
        return isinstance(value, (six.text_type, six.string_types, datetime.datetime))
    elif type_def == 'boolean':
        return (isinstance(value, bool) or
                (isinstance(value, (six.text_type, six.string_types,)) and
                 value.lower() in ['true', 'false'])
                )
    else:
        return False


def _get_example_from_prop_spec(specification, prop_spec, mode):  # ='sample-max'):
    """Return an example value from a property specification.

    :param prop_spec: the specification of the property.
    :param mode: sample-max, sample-min, default
    :return: An example value
    """
    # Read example directly from (X-)Example or Default value
    if mode == 'default':
        easy_keys = ['default']
    else:
        easy_keys = ['example', 'x-example', 'default']
    for key in easy_keys:
        if key in prop_spec.keys():  # and _use_example:
            return prop_spec[key]
    # Enum
    if 'enum' in prop_spec.keys():
        return prop_spec['enum'][0]
    # From definition
    if '$ref' in prop_spec.keys():
        return _example_from_definition(specification, prop_spec, mode)
    # Complex type
    if 'type' not in prop_spec:
        raise GcdtError(msg='something is wrong! found complex type!')
        #return _example_from_complex_def(specification, prop_spec, mode)
    # Object - read from properties, without references
    if prop_spec['type'] == 'object':
        example = _get_example_from_properties(specification, prop_spec, mode)
        if example:
            return example
        return None
    # Array
    if prop_spec['type'] == 'array' or (isinstance(prop_spec['type'], list)
            and prop_spec['type'][0] == 'array'):
        return _example_from_array_spec(specification, prop_spec, mode)
    # File
    if prop_spec['type'] == 'file':
        return (StringIO('my file contents'), 'hello world.txt')
    # Date time
    if 'format' in prop_spec.keys() and prop_spec['format'] == 'date-time':
        return _get_example_from_basic_type('datetime', mode)[0]
    # List
    if isinstance(prop_spec['type'], list):
        return _get_example_from_basic_type(prop_spec['type'][0], mode)[0]

    # Default - basic type
    logging.info("falling back to basic type, no other match found")
    if mode == 'default':
        # there is no 'default' -> no value!
        return None
    return _get_example_from_basic_type(prop_spec['type'], mode)[0]


def _get_example_from_properties(specification, spec, mode):
    """Get example from the properties of an object defined inline.

    Args:
        prop_spec: property specification you want an example of.

    Returns:
        An example for the given spec
    """
    local_spec = deepcopy(spec)

    # Handle additionalProperties if they exist
    # we replace additionalProperties with two concrete
    # properties so that examples can be generated
    if 'additionalProperties' in local_spec:
        if 'properties' not in local_spec:
            local_spec['properties'] = {}
        local_spec['properties'].update({
            'any_prop1': {'type': 'string'},
            'any_prop2': {'type': 'integer'},
        })
        local_spec.pop('additionalProperties', None)

    example = {}
    properties = local_spec.get('properties')
    if properties is not None:
        required = local_spec.get('required', properties.keys())

        for inner_name, inner_spec in properties.items():
            if mode in ['default', 'sample-min'] and inner_name not in required:
                continue
            if mode == 'default' and 'default' not in inner_spec:
                continue
            partial = _get_example_from_prop_spec(specification, inner_spec, mode)
            # While get_example_from_prop_spec is supposed to return a list,
            # we don't actually want that when recursing to build from
            # properties
            if isinstance(partial, list):
                partial = partial[0]
            example[inner_name] = partial

    return example


def _get_example_from_basic_type(type, mode):
    """Get example from the given type.

    Args:
        type: the type you want an example of.

    Returns:
        An array with two example values of the given type.
    """
    if type == 'integer':
        return [42, 24]
    elif type == 'number':
        return [5.5, 5.5]
    elif type == 'string':
        return ['string', 'string2']
    elif type == 'datetime':
        return ['2015-08-28T09:02:57.481Z', '2015-08-28T09:02:57.481Z']
    elif type == 'boolean':
        return [False, True]
    elif type == 'null':
        return ['null', 'null']


def _example_from_definition(specification, prop_spec, mode):
    """Get an example from a property specification linked to a definition.

    Args:
        prop_spec: specification of the property you want an example of.

    Returns:
        An example.
    """
    # Get value from definition
    definition_name = _get_definition_name_from_ref(prop_spec['$ref'])

    example_dict = _build_one_definition_example(specification, definition_name, mode)
    if example_dict:
        return example_dict


def _example_from_array_spec(specification, prop_spec, mode):
    """Get an example from a property specification of an array.

    Args:
        prop_spec: property specification you want an example of.

    Returns:
        An example array.
    """
    # if items is a list, then each item has its own spec
    if isinstance(prop_spec['items'], list):
        return [_get_example_from_prop_spec(specification, item_prop_spec, mode)
                for item_prop_spec in prop_spec['items']]
    # Standard types in array
    elif 'type' in prop_spec['items'].keys():
        if 'format' in prop_spec['items'].keys() and prop_spec['items']['format'] == 'date-time':
            return _get_example_from_basic_type('datetime', mode)
        else:
            if mode == 'default':
                return None
            return _get_example_from_basic_type(prop_spec['items']['type'], mode)

    # Array with definition
    elif ('$ref' in prop_spec['items'].keys() or
              ('schema' in prop_spec and'$ref' in prop_spec['schema']['items'].keys())):
        # Get value from definition
        definition_name = _get_definition_name_from_ref(prop_spec['items']['$ref']) or \
                          _get_definition_name_from_ref(prop_spec['schema']['items']['$ref'])
        example_dict = _build_one_definition_example(
            specification, definition_name, mode)
        if not isinstance(example_dict, dict):
            return [example_dict]
        return_value = {}
        for example_name, example_value in example_dict.items():
            return_value[example_name] = example_value
        return [return_value]
    elif 'properties' in prop_spec['items']:
        prop_example = {}
        for prop_name, prop_spec in prop_spec['items']['properties'].items():
            example = _get_example_from_prop_spec(specification, prop_spec, mode)
            if example is not None:
                prop_example[prop_name] = example
        return [prop_example]


def _get_definition_name_from_ref(ref):
    """Get the definition name of the given $ref value(Swagger value).

    Args:
        ref: ref value (ex: "#/definitions/CustomDefinition")

    Returns:
        The definition name corresponding to the ref.
    """
    p = re.compile('#\/definitions\/(.*)')
    definition_name = re.sub(p, r'\1', ref)
    return definition_name
