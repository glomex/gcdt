# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import textwrap

from nose.tools import assert_equal

from gcdt.yugen_core import _compile_template, _arn_to_uri, \
    _get_region_and_account_from_lambda_arn, \
    _convert_method_settings_into_operations
from gcdt_testtools.helpers import create_tempfile, cleanup_tempfiles


def _setup():
    return {'temp_files': []}


def _teardown(temp_files=[]):
    for t in temp_files:
        os.unlink(t)


def test_compile_template(cleanup_tempfiles):
    swagger_template_file = create_tempfile(textwrap.dedent("""\
        ---
          swagger: "2.0"
          info:
            title: {{apiName}}
            description: {{apiDescription}}
            version: "0.0.1"
          basePath: "/{{apiBasePath}}"
          host: "{{apiHostname}}"
    """))
    cleanup_tempfiles.append(swagger_template_file)

    template_params = {
        'apiName': 'apiName',
        'apiDescription': 'apiDescription',
        'apiBasePath': 'apiBasePath',
        'apiHostname': 'apiHostname'
    }

    expected = textwrap.dedent("""\
        ---
          swagger: "2.0"
          info:
            title: apiName
            description: apiDescription
            version: "0.0.1"
          basePath: "/apiBasePath"
          host: "apiHostname"
    """)

    assert_equal(_compile_template(swagger_template_file, template_params),
                 expected)


def test_get_region_and_account_from_lambda_arn():
    lambda_arn = 'arn:aws:lambda:eu-west-1:644239850139:function:dp-dev-process-keyword-extraction'
    lambda_region, lambda_account_id = \
        _get_region_and_account_from_lambda_arn(lambda_arn)
    assert_equal(lambda_region, 'eu-west-1')
    assert_equal(lambda_account_id, '644239850139')


def test_arn_to_uri():
    lambda_arn = 'arn:aws:lambda:eu-west-1:644239850139:function:dp-dev-process-keyword-extraction'
    uri = _arn_to_uri(lambda_arn, 'ACTIVE')
    assert_equal(uri,
                 'arn:aws:apigateway:eu-west-1:lambda:path/2015-03-31/functions/arn:aws:lambda:eu-west-1:644239850139:function:dp-dev-process-keyword-extraction:ACTIVE/invocations')


def test_convert_method_settings_into_operations():
    method_settings = {
        '/billing/MES/final/GET': {
            'cachingEnabled': False,
            'throttlingBurstLimit': 123
        },
        '/billing/MES/sth/GET': {
            'cachingEnabled': True,
            'throttlingBurstLimit': 321
        }
    }
    expected = [
        {
            u'op': u'replace',
            u'path': u'/billing/MES/final/GET/caching/enabled',
            u'value': u'false'
        },
        {
            u'op': u'replace',
            u'path': u'/billing/MES/final/GET/throttling/burstLimit',
            u'value': 123
        },
        {
            u'op': u'replace',
            u'path': u'/billing/MES/sth/GET/caching/enabled',
            u'value': u'true'
        },
        {
            u'op': u'replace',
            u'path': u'/billing/MES/sth/GET/throttling/burstLimit',
            u'value': 321
        }
    ]
    actual = _convert_method_settings_into_operations(method_settings)
    assert actual == expected
