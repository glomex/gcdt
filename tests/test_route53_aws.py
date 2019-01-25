# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from nose.tools import assert_equal
from troposphere.ec2 import Instance

import pytest
from gcdt import route53

from gcdt_testtools.helpers_aws import awsclient, check_preconditions


@pytest.mark.aws
@check_preconditions
def test_create_record_with_given_hostname(awsclient):
    # used in cloudformation!
    result_record = route53.create_record(
        awsclient,
        'TESTPREFIX',
        '120.0.0.1',
        host_zone_name='TEST.HOST.ZONE.',
    )

    # Compare HostedZoneName
    assert_equal(result_record.HostedZoneName, 'TEST.HOST.ZONE.')
    # Compare Name : DNS name used as URL later on
    assert_equal(result_record.Name.data, {'Fn::Join': ['', ['TESTPREFIX.', 'TEST.HOST.ZONE.']]})
    # Compare ResourceRecords : The target for the route
    assert_equal(result_record.ResourceRecords, ['120.0.0.1'])
    # Compare Type : The default should be 'A'
    assert_equal(result_record.Type, 'A')
    # Compare TTL
    assert_equal(result_record.TTL, route53.TTL_DEFAULT)


@pytest.mark.aws
@check_preconditions
def test_create_record_with_given_hostname_cname(awsclient):
    # used in cloudformation!
    result_record = route53.create_record(
        awsclient,
        'TESTPREFIX',
        '120.0.0.1',
        host_zone_name='TEST.HOST.ZONE.',
        type='CNAME'
    )

    # Compare HostedZoneName
    assert_equal(result_record.HostedZoneName, 'TEST.HOST.ZONE.')
    # Compare Name : DNS name used as URL later on
    assert_equal(result_record.Name.data, {'Fn::Join': ['', ['TESTPREFIX.', 'TEST.HOST.ZONE.']]})
    # Compare ResourceRecords : The target for the route
    assert_equal(result_record.ResourceRecords, ['120.0.0.1'])
    # Compare Type
    assert_equal(result_record.Type, 'CNAME')
    # Compare TTL
    assert_equal(result_record.TTL, route53.TTL_DEFAULT)


def test_create_record_with_given_hostname_target_instance():
    # used in cloudformation!
    instance = Instance('testEC2')

    result_record = route53.create_record(
        awsclient,
        'TESTPREFIX',
        instance,
        host_zone_name='TEST.HOST.ZONE.',
    )

    # Compare HostedZoneName
    assert_equal(result_record.HostedZoneName, 'TEST.HOST.ZONE.')
    # Compare Name : DNS name used as URL later on
    assert_equal(result_record.Name.data, {'Fn::Join': ['', ['TESTPREFIX.', 'TEST.HOST.ZONE.']]})
    # Compare ResourceRecords : The target for the route
    assert_equal(result_record.ResourceRecords[0].data, {'Fn::GetAtt': ['testEC2', 'PrivateIp']})
    # Compare Type
    assert_equal(result_record.Type, 'A')
    # Compare TTL
    assert_equal(result_record.TTL, route53.TTL_DEFAULT)


@pytest.mark.aws
@check_preconditions
def test_retrieve_stack_host_zone_name(awsclient):
    zn = route53._retrieve_stack_host_zone_name(awsclient, 'infra-dev')
    print(zn)


'''
def _retrieve_stack_host_zone_name():
    """
    Use service discovery to get the host zone name from the default stack

    :return: Host zone name as string
    """
    global _host_zone_name

    if _host_zone_name is not None:
        return _host_zone_name

    env = get_env()

    if env is None:
        print('Please set environment...')
        sys.exit()

    default_stack_name = 'dp-' + env
    default_stack_output = get_outputs_for_stack(default_stack_name)

    if HOST_ZONE_NAME__STACK_OUTPUT_NAME not in default_stack_output:
        print('Please debug why default stack '{}' does not contain '{}'...'.format(
            default_stack_name,
            HOST_ZONE_NAME__STACK_OUTPUT_NAME,
        ))
        sys.exit()

    _host_zone_name = default_stack_output[HOST_ZONE_NAME__STACK_OUTPUT_NAME] + '.'
    return _host_zone_name
'''