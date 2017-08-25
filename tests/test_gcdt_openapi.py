# -*- coding: utf-8 -*-
"""tools to generate from openapi spec
"""
from __future__ import unicode_literals, print_function

import pytest

from gcdt.gcdt_openapi import build_one_definition_example, read_openapi_ordered, \
    _check_type, _get_example_from_prop_spec, _get_definition_name_from_ref, \
    _example_from_array_spec, _example_from_definition, _get_example_from_basic_type, \
    _get_example_from_properties
from . import here


@pytest.fixture
def swagger_spec():
    spec = read_openapi_ordered(here('resources/gcdt_openapi/swagger.yaml'))
    return spec


def test_build_one_definition_example_sample_max(swagger_spec):
    pet_definition_example = {
        'category': {
            'id': 42,
            'name': 'string'
        },
        'status': 'string',
        'name': 'doggie',
        'tags': [
            {
                'id': 42,
                'name': 'string'
            }
        ],
        'photoUrls': [
            'string',
            'string2'
        ],
        'id': 42
    }
    assert build_one_definition_example(swagger_spec, 'Pet', 'sample-max') == pet_definition_example

    # Test wrong definition
    swagger_spec['definitions']['Pet']['properties']['category']['$ref'] = '#/definitions/Error'
    # TODO
    #assert not build_one_definition_example(swagger_spec, 'Pet', 'sample-max')

    # Test wrong def name
    assert not build_one_definition_example(swagger_spec, 'Error', 'sample-max')


@pytest.fixture
def swagger_defaults_spec():
    spec = read_openapi_ordered(here('resources/gcdt_openapi/swagger_defaults.yaml'))
    return spec


def test_build_one_definition_example_default(swagger_defaults_spec):
    tag_defaults = {'id': 8}
    assert build_one_definition_example(swagger_defaults_spec, 'Tag', 'default') == tag_defaults

    pet_defaults = {'name': 'bolt', 'tags': [{'id': 8}]}
    assert build_one_definition_example(swagger_defaults_spec, 'Pet', 'default') == pet_defaults


def test_build_one_definition_example_sample_min(swagger_defaults_spec):
    tag_defaults = {'id': 5}
    assert build_one_definition_example(swagger_defaults_spec, 'Tag', 'sample-min') == tag_defaults


def test_check_type():
    # Test int
    assert _check_type(int(5), 'integer')
    assert _check_type(int(5), 'number')
    assert _check_type('5', 'integer')
    assert not _check_type(int(5), 'string')
    assert not _check_type(int(5), 'boolean')

    # Test float
    assert _check_type(5.5, 'number')
    assert not _check_type(5.5, 'string')
    assert not _check_type(5.5, 'boolean')

    # Test string
    assert not _check_type('test', 'integer')
    assert not _check_type('test', 'number')
    assert _check_type('test', 'string')
    assert not _check_type('test', 'boolean')

    # Test boolean
    assert not _check_type(False, 'number')
    assert not _check_type(False, 'string')
    assert _check_type(False, 'boolean')

    # Test other
    assert not _check_type(object, 'string')


def test_get_example_from_prop_spec(swagger_spec):
    prop_spec = {}

    # Primitive types
    prop_spec['type'] = 'integer'
    assert _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max') == 42
    prop_spec['type'] = 'number'
    assert _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max') == 5.5
    prop_spec['type'] = 'string'
    assert _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max') == 'string'
    prop_spec['type'] = 'boolean'
    assert not _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max')

    # Array
    prop_spec['type'] = 'array'
    prop_spec['items'] = {}

    # Primitive types
    prop_spec['items']['type'] = 'integer'
    assert _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max') == [42, 24]
    prop_spec['items']['type'] = 'number'
    assert _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max') == [5.5, 5.5]
    prop_spec['items']['type'] = 'string'
    assert _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max') == ['string',
                                                                    'string2']
    prop_spec['items']['type'] = 'boolean'
    assert _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max') == [False, True]

    # definition
    del prop_spec['items']['type']
    prop_spec['items']['$ref'] = '#/definitions/Tag'
    assert _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max') == \
        [{'id': 42, 'name': 'string'}]

    # Inline complex
    prop_spec = {
        'type': 'object',
        'properties': {
            'error': {
                'type': 'object',
                'properties': {
                    'code': {'type': 'string'},
                    'title': {'type': 'string'},
                    'detail': {'type': 'string'},
                },
                'required': ['code', 'title', 'detail'],
            },
        },
        'required': ['error'],
    }
    example = _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max')
    assert example == [
        {'error': {'code': 'string', 'detail': 'string', 'title': 'string'}}]


def test_get_example_from_prop_spec_with_additional_properties(swagger_spec):
    prop_spec = {
        'type': 'object',
        'properties': {
            'error': {
                'type': 'object',
                'properties': {
                    'code': {'type': 'string'},
                    'title': {'type': 'string'},
                    'detail': {'type': 'string'},
                },
                'required': ['code', 'title', 'detail'],
            },
        },
        'required': ['error'],
    }

    # additionalProperties - $ref (complex prop_spec with required keys)
    prop_spec['additionalProperties'] = {'$ref': '#/definitions/Category'}
    example = _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max')
    assert example == {
        'any_prop2': {'id': 42, 'name': 'string'},
        'any_prop1': {'id': 42, 'name': 'string'},
        'error': {'code': 'string', 'detail': 'string', 'title': 'string'},
    }

    # additionalProperties - string (with complex prop_spec without required keys)
    del prop_spec['required']
    prop_spec['additionalProperties'] = {'type': 'string'}
    example = _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max')
    assert example == {
        'any_prop2': 'string',
        'any_prop1': 'string',
    }

    # additionalProperties - integer (prop spec with only additional properties)
    easy_prop_spec = {
        'type': 'object',
        'additionalProperties': {'type': 'integer', 'format': 'int64'},
    }
    example = _get_example_from_prop_spec(swagger_spec, easy_prop_spec, 'sample-max')
    assert example == {'any_prop1': 42, 'any_prop2': 42}

    # additionalProperties - dict not satisfying any definition
    #  (with complex prop_spec without required keys)
    prop_spec['additionalProperties'] = {
        'type': 'object',
        'properties': {
            'food': {'type': 'string'},
            'drink': {'type': 'number', 'format': 'double'},
            'movies': {'type': 'boolean'},
        }
    }
    example = _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max')
    assert example == {
        'any_prop2': {'food': 'string', 'movies': False, 'drink': 5.5},
        'any_prop1': {'food': 'string', 'movies': False, 'drink': 5.5},
    }

    # additionalProperties - dict satisfying the 'Category' definition
    prop_spec['additionalProperties'] = {
        'type': 'object',
        'properties': {
            'id': {'type': 'integer', 'format': 'int64'},
            'name': {'type': 'string'},
        }
    }
    example = _get_example_from_prop_spec(swagger_spec, prop_spec, 'sample-max')
    assert example == {
        'any_prop2': {'id': 42, 'name': 'string'},
        'any_prop1': {'id': 42, 'name': 'string'},
    }


def test_get_example_from_prop_spec_default():
    # required but no default
    prop_spec = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'integer',
                'format': 'int64'
            },
            'name': {
                'type': 'string',
                'example': 'not to use!'
            },
        },
        'required': ['name'],
        'additionalProperties': True
    }
    example = _get_example_from_prop_spec({}, prop_spec, 'default')
    assert example is None


'''
def test_get_example_from_prop_spec_default_ref(swagger_defaults_spec):
    # required but no default
    prop_spec = swagger_array_spec['definitions']['Tag']
    example = _get_example_from_prop_spec({}, prop_spec, 'default')
    assert example is None
'''


def test_get_example_from_properties():
    # Object - read from properties, without references
    prop_spec = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'integer',
                'format': 'int64'
            },
            'name': {
                'type': 'string'
            }
        }
        #'additionalProperties': True
    }
    example, additional_property = _get_example_from_properties({}, prop_spec, 'sample-max')
    assert example == {u'id': 42, u'name': u'string'}
    assert additional_property == False  # TODO ???


def test_get_example_from_basic_type():
    sample = _get_example_from_basic_type('integer', 'sample-max')
    assert sample == [42, 24]

    sample = _get_example_from_basic_type('string', 'sample-max')
    assert sample == ['string', 'string2']


def test_example_from_definition(swagger_spec):
    prop_spec = {
        '$ref': '#/definitions/Tag'
    }
    sample = _example_from_definition(swagger_spec, prop_spec, 'sample-max')
    assert sample == {'id': 42, 'name': 'string'}


@pytest.fixture
def swagger_array_spec():
    spec = read_openapi_ordered(here('resources/gcdt_openapi/swagger_arrays.yaml'))
    return spec


def test_example_from_array_spec_string_array():
    #prop_spec = OrderedDict([
    #    ('type', 'array'),
    #    ('items', OrderedDict([
    #        ('type', 'string')
    #    ]))
    #])
    prop_spec = {
        'type': 'array',
        'items': {
            'type': 'string'
        }
    }

    sample = _example_from_array_spec({}, prop_spec, 'sample-max')
    assert sample == [u'string', u'string2']


def test_example_from_array_spec_default(swagger_defaults_spec):
    # default for the required props
    prop_spec = {
        'type': 'array',
        'items': {'$ref': '#/definitions/Tag'}
    }

    sample = _example_from_array_spec(swagger_defaults_spec, prop_spec, 'default')
    assert sample == [{'id': 8}]

    # no default if not required
    prop_spec = {
        'description': 'this is required but we do not have a default!',
        'type': 'array',
        'items': {
           'type': 'string'
        }
    }

    sample = _example_from_array_spec(swagger_defaults_spec, prop_spec, 'default')
    assert sample is None


def test_example_from_array_spec_widget_array(swagger_array_spec):
    prop_spec = swagger_array_spec['definitions']['WidgetArray']

    sample = _example_from_array_spec(swagger_array_spec, prop_spec, 'sample-max')
    assert sample == [{'prop1': 'string', 'prop2': 'string'}]


def test_get_definition_name_from_ref(swagger_spec):
    assert _get_definition_name_from_ref(
        '#/definitions/Pet') == 'Pet'



# TODO missing testcases
# * invalid swagger file
# * _definition_from_example
# * _example_from_complex_def
# * _example_from_array_spec - 'properties' in prop_spec['items']
# *
