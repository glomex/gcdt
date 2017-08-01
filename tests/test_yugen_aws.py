# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging

from nose.tools import assert_equal, assert_not_in
import pytest

from gcdt import utils
from gcdt.yugen_core import deploy_api, delete_api, delete_api_key, \
    create_api_key, _template_variables_to_dict
from gcdt_testtools import helpers
from gcdt_testtools.helpers_aws import check_preconditions
from gcdt_testtools.helpers_aws import awsclient  # fixtures!

log = logging.getLogger(__name__)


@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_apis(awsclient):
    apis = []
    yield apis
    # cleanup
    for i in apis:
        delete_api(awsclient, i)


@pytest.fixture(scope='function')  # 'function' or 'module'
def cleanup_api_keys(awsclient):
    items = []
    yield items
    # cleanup
    for i in items:
        delete_api_key(awsclient, i)


@pytest.mark.aws
@check_preconditions
def test_create_api(awsclient, cleanup_api_keys, cleanup_apis):
    log.info('running test_create_api')

    temp_string = utils.random_string()
    api_name = 'unittest-gcdt-sample-api-%s' % temp_string
    api_key_name = 'unittest-gcdt-sample-api-key-%s' % temp_string
    api_description = 'Gcdt sample API based on dp api-mock'
    target_stage = 'mock'
    api_key = create_api_key(awsclient, api_name, api_key_name)
    cleanup_api_keys.append(api_key)

    lambdas = []
    deploy_api(
        awsclient=awsclient,
        api_name=api_name,
        api_description=api_description,
        stage_name=target_stage,
        api_key=api_key,
        lambdas=lambdas,
        cache_cluster_enabled=False
    )
    cleanup_apis.append(api_name)


@pytest.mark.aws
@check_preconditions
def test_template_variables_to_dict_custom_hostname(awsclient):
    api_name = 'apiName'
    api_description = 'apiDescription'
    api_target_stage = 'mock'

    client_api = awsclient.get_client('apigateway')
    result = _template_variables_to_dict(
        client_api, api_name, api_description, api_target_stage,
        custom_hostname='chn', custom_base_path='cbp')
    assert_equal(result['apiName'], api_name)
    assert_equal(result['apiDescription'], api_description)
    assert_equal(result['apiBasePath'], 'cbp')
    assert_equal(result['apiHostname'], 'chn')


@pytest.mark.aws
@check_preconditions
def test_template_variables_to_dict(awsclient):
    api_name = 'apiName'
    api_description = 'apiDescription'
    api_target_stage = 'mock'
    client_api = awsclient.get_client('apigateway')
    result = _template_variables_to_dict(client_api, api_name,
                                         api_description, api_target_stage)
    assert_equal(result['apiName'], api_name)
    assert_equal(result['apiDescription'], api_description)
    assert_equal(result['apiBasePath'], 'mock')
    assert_not_in('apiHostname', result)


# FIXME: tests
# * important test "yugen deploy" without valid key, I think there is a defect!
# * test that reads config from file
# * current coverage is 35% (that is not good enough!)

# TODO missing tests
# export_to_swagger
# list_apis
# list_api_keys
# create_custom_domain
# get_lambdas
# are_credentials_still_valid
# _import_from_swagger
# _update_from_swagger
# _create_api
# _wire_api_key
# _create_deployment
# _ensure_correct_base_path_mapping
# _base_path_mapping_exists
# _record_exists_and_correct
# _create_new_custom_domain
# _template_variables_to_dict
# _ensure_lambda_permissions
# _invoke_lambda_permission_exists
# _custom_domain_name_exists
# _basepath_to_string_if_null
#
