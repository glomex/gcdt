# -*- coding: utf-8 -*-
"""The kumo_util file contains stuff that is used for example in cloudformation.py
templates or from other external code.
"""
from __future__ import unicode_literals, print_function
import sys

import troposphere
from troposphere.cloudformation import AWSCustomObject


PY3 = sys.version_info[0] >= 3

if PY3:
    basestring = str


class StackLookup(object):
    """Class to handle stack lookups
    Note: gcdt.kumo_util StackLookup(template, template, param_lambda_lookup_arn)
    is used in many cloudformation.py templates!
    """

    def __init__(self, template, param_lambda_lookup_arn,
                 param_stack_dependent_on=None):
        """Adds function to cloudformation template to lookup stack information
        :param template: The cloudformation template
        :param param_lambda_lookup_arn: The parameter stating the ARN of the
            COPS provided Lambda lookup function
        :param param_stack_dependent_on: The parameter stating the stack name
            which should be lookedup from (Default: None)
        """
        if param_stack_dependent_on is not None:
            class CustomStackOutput(AWSCustomObject):
                resource_type = 'Custom::StackOutput'

                props = {
                    'ServiceToken': (basestring, True),
                    'StackName': (basestring, True)
                }

            self.__custom_stack_obj = template.add_resource(CustomStackOutput(
                'StackOutput',
                ServiceToken=troposphere.Ref(
                    param_lambda_lookup_arn
                ),
                StackName=troposphere.Ref(param_stack_dependent_on),
            ))
        else:
            class CustomStackOutput(AWSCustomObject):
                resource_type = 'Custom::StackOutput'

                props = {
                    'ServiceToken': (basestring, True)
                }

            self.__custom_stack_obj = template.add_resource(CustomStackOutput(
                'StackOutput',
                ServiceToken=troposphere.Ref(
                    param_lambda_lookup_arn
                ),
            ))

    def get_att(self, parameter, as_reference=True):
        """Retrieves an attribute from an existing stack
        :param parameter: The output parameter which should be retrieved
        :param as_reference: Is the parameter a reference (Default) or a string
        :return: Value of parameter to retrieve
        """
        if as_reference:
            return troposphere.GetAtt(
                self.__custom_stack_obj,
                troposphere.Ref(parameter)
            )
        else:
            return troposphere.GetAtt(
                self.__custom_stack_obj,
                parameter
            )


def ensure_ebs_volume_tags_autoscaling_group(awsclient, as_group_name, tags):
    # note: gcdt.kumo_util ensure_ebs_volume_tags_autoscaling_group(awsclient, ...)
    # is used in dataplatform cloudformation.py templates!
    ec2_client = awsclient.get_client('ec2')

    autoscale_filter = {
        'Name': 'tag:aws:autoscaling:groupName',
        'Values': [as_group_name]
    }
    response = ec2_client.describe_instances(Filters=[autoscale_filter])
    for r in response['Reservations']:
        for i in r['Instances']:
            ensure_ebs_volume_tags_ec2_instance(awsclient, i['InstanceId'],
                                                tags)


def ensure_ebs_volume_tags_ec2_instance(awsclient, instance_id, tags):
    # I think this is only relevant to test code!
    client_ec2 = awsclient.get_client('ec2')
    volumes = client_ec2.describe_volumes(Filters=[
        {
            'Name': 'attachment.instance-id',
            'Values': [instance_id]
        }
    ])
    for v in volumes['Volumes']:
        ensure_tags_ebs_volume(awsclient, v, tags)


def ensure_tags_ebs_volume(awsclient, volume, tags):
    client_ec2 = awsclient.get_client('ec2')
    tags_to_add = []
    if 'Tags' in volume:
        for tag in tags:
            if tag not in volume['Tags']:
                tags_to_add.append(tag)
        if tags_to_add:
            client_ec2.create_tags(Resources=[volume['VolumeId']],
                                   Tags=tags_to_add)
    else:
        client_ec2.create_tags(Resources=[volume['VolumeId']],
                               Tags=tags)
