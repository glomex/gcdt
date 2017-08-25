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


# tools to generate from openapi spec:
# * default configuration
# * min sample (only required properties)
# * max sample (all properties)

# implementation started with codebase from:
# https://github.com/Trax-air/swagger-parser/blob/master/swagger_parser/swagger_parser.py
# (MIT) version 11th Jun 2017, 8534150

# why not keep the class structure which implemented caching to speed things up??
# since we have different modes we can not have an example cache any more
# meaning a referenced definition can have different examples and defaults on
# different levels one time it is required and has a default another time this
# is not the case. therefor we need to fully evaluate the whole structure and
# can not reuse examples.


def build_one_definition_example(specification, def_name, mode):
    """Build the example for the given definition.

    :param def_name: Name of the definition.
    :param mode: sample-max, sample-min, default
    :return: True if the example has been created, False if an error occured.
    """
    #if def_name in _definitions_example.keys():  # Already processed
    #    return True
    if def_name not in specification['definitions'].keys():  # Def does not exist
        return False  # TODO

    #_definitions_example[def_name] = {}
    definitions_example = {}
    def_spec = specification['definitions'][def_name]

    if def_spec.get('type') == 'array' and 'items' in def_spec:
        item = _get_example_from_prop_spec(def_spec['items'], mode)
        definitions_example[def_name] = [item]
        return definitions_example

    if 'properties' not in def_spec:
        definitions_example[def_name] = _get_example_from_prop_spec(def_spec, mode)
        return definitions_example

    # Get properties example value
    for prop_name, prop_spec in def_spec['properties'].items():
        required = prop_name in def_spec.get('required', [])
        #default = 'default' in prop_spec
        #if mode == 'sample-max' or (required and default):
        if mode == 'sample-max' or required:
            #print('default: %s' % default)
            example = _get_example_from_prop_spec(specification, prop_spec, mode)
            if example is None:
                continue
                #return False
            #_definitions_example[def_name][prop_name] = example
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
    # default mode
    if mode == 'default':
        # Array
        if 'type' in prop_spec and (prop_spec['type'] == 'array' or (
                'type' in prop_spec and isinstance(prop_spec['type'], list)
                and prop_spec['type'][0] == 'array')):
            return _example_from_array_spec(specification, prop_spec, mode)
        return None
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
        example, additional_properties = \
            _get_example_from_properties(specification, prop_spec, mode)
        if additional_properties:
            return example
        return [example]
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
    #if mode == 'default':
    #    # there is no 'default' -> no value!
    #    return []
    return _get_example_from_basic_type(prop_spec['type'], mode)[0]


def _get_example_from_properties(specification, spec, mode):
    """Get example from the properties of an object defined inline.

    Args:
        prop_spec: property specification you want an example of.

    Returns:
        An example for the given spec
        A boolean, whether we had additionalProperties in the spec, or not
    """
    local_spec = deepcopy(spec)

    # Handle additionalProperties if they exist
    # we replace additionalProperties with two concrete
    # properties so that examples can be generated
    additional_property = False
    if 'additionalProperties' in local_spec:
        additional_property = True
        if 'properties' not in local_spec:
            local_spec['properties'] = {}
        local_spec['properties'].update({
            'any_prop1': local_spec['additionalProperties'],
            'any_prop2': local_spec['additionalProperties'],
        })
        del(local_spec['additionalProperties'])
        required = local_spec.get('required', [])
        required += ['any_prop1', 'any_prop2']
        local_spec['required'] = required

    example = {}
    properties = local_spec.get('properties')
    if properties is not None:
        required = local_spec.get('required', properties.keys())

        for inner_name, inner_spec in properties.items():
            if inner_name not in required:
                continue
            partial = _get_example_from_prop_spec(specification, inner_spec, mode)
            # While get_example_from_prop_spec is supposed to return a list,
            # we don't actually want that when recursing to build from
            # properties
            if isinstance(partial, list):
                partial = partial[0]
            example[inner_name] = partial

    return example, additional_property


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
    print('definition name: %s' % definition_name)

    #if _build_one_definition_example(definition_name, mode):
    example_dict = build_one_definition_example(specification, definition_name, mode)
    if example_dict:
        #example_dict = _definitions_example[definition_name]
        if not isinstance(example_dict, dict):
            return example_dict
        example = dict((example_name, example_value) for example_name, example_value in example_dict.items())
        return example


def _example_from_array_spec(specification, prop_spec, mode):
    """Get an example from a property specification of an array.

    Args:
        prop_spec: property specification you want an example of.

    Returns:
        An example array.
    """
    # if items is a list, then each item has its own spec
    if isinstance(prop_spec['items'], list):
        #print('a')
        return [_get_example_from_prop_spec(specification, item_prop_spec, mode)
                for item_prop_spec in prop_spec['items']]
    # Standard types in array
    elif 'type' in prop_spec['items'].keys():
        #print('b')
        if 'format' in prop_spec['items'].keys() and prop_spec['items']['format'] == 'date-time':
            return _get_example_from_basic_type('datetime', mode)
        else:
            if mode == 'default':
                return None
            return _get_example_from_basic_type(prop_spec['items']['type'], mode)

    # Array with definition
    elif ('$ref' in prop_spec['items'].keys() or
              ('schema' in prop_spec and'$ref' in prop_spec['schema']['items'].keys())):
        #print('c')
        # Get value from definition
        definition_name = _get_definition_name_from_ref(prop_spec['items']['$ref']) or \
                          _get_definition_name_from_ref(prop_spec['schema']['items']['$ref'])
        #if _build_one_definition_example(definition_name, mode):
        #    example_dict = _definitions_example[definition_name]
        example_dict = build_one_definition_example(
            specification, definition_name, mode)
        if not isinstance(example_dict, dict):
            return [example_dict]
        #if len(example_dict) == 1:
        if False:
            # we can not collapse the structure!
            pass
            #try:  # Python 2.7
            #    res = example_dict[example_dict.keys()[0]]
            #except TypeError:  # Python 3
            #    res = example_dict[list(example_dict)[0]]
            #return res
        else:
            return_value = {}
            for example_name, example_value in example_dict.items():
                return_value[example_name] = example_value
            return [return_value]
    elif 'properties' in prop_spec['items']:
        #print('d')
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
