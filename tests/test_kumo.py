# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import json
from tempfile import NamedTemporaryFile

from nose.tools import assert_dict_equal
from nose.tools import assert_equal, assert_true, \
    assert_regexp_matches, assert_list_equal, raises
import pytest

from gcdt.kumo_core import _generate_parameters, \
    load_cloudformation_template, write_template_to_file, _get_stack_name, \
    _get_stack_policy, _get_stack_policy_during_update, _get_conf_value, \
    _generate_parameter_entry, _call_hook, generate_template
from gcdt.utils import fix_old_kumo_config
from gcdt.gcdt_config_reader import read_json_config

from gcdt_testtools.helpers import cleanup_tempfiles, temp_folder  # fixtures!
from gcdt_testtools.helpers import Bunch
from . import here


def test_load_cloudformation_template(cleanup_tempfiles):
    tf = NamedTemporaryFile(delete=False, suffix='py')
    open(tf.name, 'w').write('def plus(a, b):\n    return a+b')
    cleanup_tempfiles.append(tf.name)

    module, success = load_cloudformation_template(tf.name)
    assert_equal(success, True)
    assert_equal(module.plus(1, 2), 3)


def test_cloudformation_template_not_available():
    module, success = load_cloudformation_template()
    assert_equal(module, None)
    assert_equal(success, False)


def test_load_cloudformation_template_from_cwd(temp_folder):
    # prepare dummy template for test
    open('cloudformation.py', 'w').write('def plus(a, b):\n    return a+b\n')

    module, success = load_cloudformation_template()
    assert_true(success, True)
    assert_equal(module.plus(1, 2), 3)


def test_simple_cloudformation_stack():
    # read the template
    template_path = here(
        'resources/simple_cloudformation_stack/cloudformation.py')
    #config_path = here(
    #    'resources/simple_cloudformation_stack/settings_dev.conf')

    cloudformation, success = load_cloudformation_template(template_path)
    assert_true(success)

    config = {
        'stack': {
            'StackName': "infra-dev-kumo-sample-stack"
        },
        'parameters': {
            'InstanceType': "t2.micro"
        }
    }

    expected_templ_file_name = '%s-generated-cf-template.json' % \
                               _get_stack_name(config)
    actual = write_template_to_file(config, generate_template({}, config, cloudformation))
    assert_equal(actual, expected_templ_file_name)


def _create_simple_cf():
    # use Bunch to create group of variables:
    # cf = Bunch(datum=y, squared=y*y, coord=x)
    cf = Bunch()
    return cf


def test_simple_cloudformation_stack_default():
    cf = _create_simple_cf()
    stack_policy = _get_stack_policy(cf)
    # policy defined in _get_stack_policy is used
    assert_regexp_matches(stack_policy, '{"Statement":')


def test_simple_cloudformation_stack_custom():
    def gsp():
        return 'have indiv. policy'
    cf = _create_simple_cf()
    cf.get_stack_policy = gsp
    stack_policy = _get_stack_policy(cf)
    assert_equal(stack_policy, 'have indiv. policy')


def test_simple_cloudformation_stack_during_update_custom():
    def gsp():
        return 'have indiv. policy'
    cf = _create_simple_cf()
    cf.get_stack_policy_during_update = gsp
    stack_policy = _get_stack_policy_during_update(cf, False)
    assert_equal(stack_policy, 'have indiv. policy')


def test_simple_cloudformation_stack_during_update_override_custom():
    # test make sure override has no impact on custom policy
    def gsp():
        return 'have indiv. policy'
    cf = _create_simple_cf()
    cf.get_stack_policy_during_update = gsp
    stack_policy = _get_stack_policy_during_update(cf, True)
    assert_equal(stack_policy, 'have indiv. policy')


def test_simple_cloudformation_stack_during_update_default():
    cf = _create_simple_cf()
    stack_policy = _get_stack_policy_during_update(cf, False)
    assert_regexp_matches(stack_policy, '{"Statement":')
    assert_equal('Deny', json.loads(stack_policy)['Statement'][1]['Effect'])
    assert_list_equal(["Update:Replace", "Update:Delete"],
                      json.loads(stack_policy)['Statement'][1]['Action'])


def test_simple_cloudformation_stack_during_update_override_default():
    cf = _create_simple_cf()
    stack_policy = _get_stack_policy_during_update(cf, True)
    assert_regexp_matches(stack_policy, '{"Statement":')


def test_parameter_substitution():
    expected = [
        {
            'ParameterKey': 'ConfigOne',
            'ParameterValue': 'value1',
            'UsePreviousValue': False
        },
        {
            'ParameterKey': 'ConfigTwo',
            'ParameterValue': 'value2,value3',
            'UsePreviousValue': False
        }
    ]
    conf = {
        'parameters': {
            'ConfigOne': 'value1',
            'ConfigTwo': ['value2', 'value3']
        }
    }

    converted_conf = _generate_parameters(conf)
    assert_equal(converted_conf, expected)


def test_parameter_substitution_reserved_terms():
    conf = {
        'parameters': {
            'ConfigOne': 'value1'
        },
        'stack': {
            'StackName': 'value2',
            'TemplateBody': 'value3',
            'artifactBucket': 'value4',
        }
    }
    expected = [
        {
            'ParameterKey': 'ConfigOne',
            'ParameterValue': 'value1',
            'UsePreviousValue': False
        }
    ]
    converted_conf = _generate_parameters(conf)
    assert_equal(converted_conf, expected)


def test_get_conf_value():
    config = {
        'parameters': {
            'ConfigOne': 'value1'
        }
    }
    assert_equal(_get_conf_value(config, 'ConfigOne'), 'value1')


def test_get_conf_value_list():
    config = {
        'parameters': {
            'ConfigOne': ['a', 'b', 'c']
        }
    }
    assert_equal(_get_conf_value(config, 'ConfigOne'), 'a,b,c')


@raises(KeyError)
def test_get_conf_value_unknown():
    config = {
        'parameters': {
            'ConfigOne': ['a', 'b', 'c']
        }
    }
    _get_conf_value(config, 'Unknown')


def test_generate_parameter_entry():
    config = {
        'parameters': {
            'ConfigOne': 'value1'
        }
    }
    assert_dict_equal(_generate_parameter_entry(config, 'ConfigOne'),
                      {
                          'ParameterKey': 'ConfigOne',
                          'ParameterValue': 'value1',
                          'UsePreviousValue': False
                      })


def _create_cfn_with_hook():
    def hook():
        pass

    # use Bunch to create group of variables:
    cfn = Bunch(pre_hook=hook)
    return cfn


def test_call_hook_unknown_hook(capsys):
    _call_hook(None, None, None, None, None, 'unknown_hook')
    out, err = capsys.readouterr()
    assert out == 'Unknown hook: unknown_hook\n'


def test_call_hook_backward_compatible(capsys):
    _call_hook(None, None, None, None, _create_cfn_with_hook(), 'pre_hook')
    out, err = capsys.readouterr()
    assert out == 'Executing pre hook...\n'


def test_call_hook_not_present(capsys):
    _call_hook(None, None, None, None, _create_cfn_with_hook(),
               'pre_create_hook')
    out, err = capsys.readouterr()
    assert out == ''


def test_new_cloudformation_template_hooks():
    template_path = here(
        'resources/simple_cloudformation_stack_hooks/cloudformation.py')
    module, success = load_cloudformation_template(template_path)
    assert_equal(success, True)

    assert module.COUNTER['register'] == 1
    # currently deregister is not called (but we need that later!)
    #assert module.COUNTER['deregister'] == 1


def test_generate_template_no_arguments():
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation.py')
    )
    context = {}
    config_simple_stack = fix_old_kumo_config(read_json_config(
        here('resources/simple_cloudformation_stack/gcdt_dev.json')
    ))['kumo']
    expected_template_body = read_json_config(
        here('resources/simple_cloudformation_stack/expected_template_body.json')
    )
    template_body = json.loads(
        generate_template(context, config_simple_stack, cloudformation_simple_stack)
    )
    assert template_body == expected_template_body


def test_generate_template_with_arguments():
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation_with_arguments.py')
    )
    context = {'foo': 'bar'}
    config_simple_stack = fix_old_kumo_config(read_json_config(
        here('resources/simple_cloudformation_stack/gcdt_dev.json')
    ))['kumo']
    expected_template_body = read_json_config(
        here('resources/simple_cloudformation_stack/expected_template_body.json')
    )
    template_body = json.loads(
        generate_template(context, config_simple_stack, cloudformation_simple_stack)
    )
    assert template_body == expected_template_body


def test_generate_template_invalid_arguments():
    cloudformation_simple_stack, _ = load_cloudformation_template(
        here('resources/simple_cloudformation_stack/cloudformation_invalid_arguments.py')
    )
    context = {'foo': 'bar'}
    config_simple_stack = fix_old_kumo_config(read_json_config(
        here('resources/simple_cloudformation_stack/gcdt_dev.json')
    ))['kumo']

    with pytest.raises(Exception) as einfo:
        generate_template(context, config_simple_stack, cloudformation_simple_stack)
    assert einfo.match(r"Arguments of 'generate_template' not as expected: \['invalid_context', 'invalid_config'\]")
