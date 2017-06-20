# -*- coding: utf-8 -*-
"""
Note: This is used in cloudformation templates (at least in parts)
A refactoring might break team-code!!
"""
from __future__ import unicode_literals, print_function
from distutils.version import StrictVersion
import re

import maya


def parse_ts(ts):
    """
    parse timestamp.
    
    :param ts: timestamp in ISO8601 format
    :return: tbd!!!
    """
    # ISO8601 = '%Y-%m-%dT%H:%M:%SZ'
    # ISO8601_MS = '%Y-%m-%dT%H:%M:%S.%fZ'
    # RFC1123 = '%a, %d %b %Y %H:%M:%S %Z'
    dt = maya.parse(ts.strip())
    return dt.datetime(naive=True)  # to_timezone default: UTC


# gets Outputs for a given StackName
def get_outputs_for_stack(awsclient, stack_name):
    """
    Read environment from ENV and mangle it to a (lower case) representation
    Note: gcdt.servicediscovery get_outputs_for_stack((awsclient, stack_name)
    is used in many cloudformation.py templates!

    :param awsclient:
    :param stack_name:
    :return: dictionary containing the stack outputs
    """
    client_cf = awsclient.get_client('cloudformation')
    response = client_cf.describe_stacks(StackName=stack_name)
    if response['Stacks'] and 'Outputs' in response['Stacks'][0]:
        result = {}
        for output in response['Stacks'][0]['Outputs']:
            result[output['OutputKey']] = output['OutputValue']
        return result


def get_ssl_certificate(awsclient, domain):
    client_iam = awsclient.get_client('iam')
    response = client_iam.list_server_certificates()
    arn = ""
    for cert in response["ServerCertificateMetadataList"]:
        if domain in cert["ServerCertificateName"]:
            print(cert['Expiration'])
            #print(datetime.now(UTC()))
            #if datetime.now(UTC()) > cert['Expiration']:
            print(maya.now().datetime())
            if maya.now().datetime() > cert['Expiration']:
                print("certificate has expired")
            else:
                arn = cert["Arn"]
                break
    return arn


def get_base_ami(awsclient, owners):
    """
    return the latest version of our base AMI
    we can't use tags for this, so we have only the name as resource
    note: this functionality is deprecated since this only works for "old"
    baseami. 
    """
    client_ec2 = awsclient.get_client('ec2')
    image_filter = [
        {
            'Name': 'state',
            'Values': [
                'available',
            ]
        },
    ]

    #latest_ts = datetime.fromtimestamp(0)
    latest_ts = maya.MayaDT(0).datetime(naive=True)
    latest_version = StrictVersion('0.0.0')
    latest_id = None
    for i in client_ec2.describe_images(
            Owners=owners,
            Filters=image_filter
            )['Images']:
        m = re.search(r'(Ops_Base-Image)_(\d+.\d+.\d+)_(\d+)$', i['Name'])
        if m:
            version = StrictVersion(m.group(2))
            timestamp = m.group(3)
            creation_date = parse_ts(i['CreationDate'])

            if creation_date > latest_ts and version >=latest_version:
                latest_id = i['ImageId']
                latest_ts = creation_date
                latest_version = version

    return latest_id
