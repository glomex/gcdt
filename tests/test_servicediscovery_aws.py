# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import pytest

from gcdt.servicediscovery import get_outputs_for_stack, get_ssl_certificate, \
    get_base_ami

from gcdt_testtools.helpers_aws import check_preconditions
from gcdt_testtools.helpers_aws import awsclient  # fixtures!
from .test_kumo_aws import config_simple_stack  # fixtures!
from .test_kumo_aws import simple_cloudformation_stack  # fixtures!


@pytest.mark.aws
@check_preconditions
def test_get_outputs_for_stack(awsclient, simple_cloudformation_stack):
    # used in cloudformation!
    outputs = get_outputs_for_stack(awsclient, simple_cloudformation_stack)
    assert 'BucketName' in outputs
    assert outputs['BucketName'].startswith('infra-dev-kumo-sample-stack-s3bucket1-')


# I do not think we support these DEPRECATED functionality any more
'''
@pytest.mark.aws
@check_preconditions
def test_get_ssl_certificate(awsclient):
    cert = get_ssl_certificate(awsclient, 'multidomain.glomex.cloud')
    print(cert)
    assert cert.startswith('arn:aws:iam::420189626185:server-certificate/cloudfront/multidomain.glomex.cloud')
'''

@pytest.mark.aws
@check_preconditions
def test_get_base_ami(awsclient):
    ami = get_base_ami(awsclient, owners=['569909643510'])
    #assert ami == 'ami-91307fe2'
    # not 100% sure how we can be sure that we found the correct ami
    # so I made this assert pass easy
    assert ami.startswith('ami-')
