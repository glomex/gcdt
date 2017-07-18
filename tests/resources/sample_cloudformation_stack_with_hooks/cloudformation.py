#!/usr/bin/env python

import troposphere

# Converted from S3_Bucket.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/
import json

from troposphere import Output, Ref, Template
from troposphere.s3 import Bucket, PublicRead

# TODO
# add resources folder to kumo for post_hook stuff
# add lambda to post_hook folder
# call lambda_deploy, lambda_invoke_lambda_delete from folder


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template S3_Bucket: template showing "
    "how to create a publicly accessible S3 bucket."
)

s3bucket1 = t.add_resource(Bucket("S3Bucket1", AccessControl=PublicRead, ))

t.add_output(Output(
    "BucketName",
    Value=Ref(s3bucket1),
    Description="Name of S3 bucket"
))

param_foo = t.add_parameter(troposphere.Parameter(
    'InstanceType',
    Description='Type of EC2 instance',
    Type='String',
))


def generate_template():
    return t.to_json()


def post_hook(awsclient, config, parameters, stack_outputs, stack_state):
    # do validations on arguments
    print('hi from hook')
    assert awsclient is not None
    #assert type(awsclient) in [AWSClient, PlaceboAWSClient] is not None

    #assert config == ConfigTree([('cloudformation', ConfigTree([('StackName', 'infra-dev-kumo-sample-stack-with-hooks'), ('InstanceType', 't2.medium')]))])
    exp_config = {
        'stack': {
            'StackName': 'infra-dev-kumo-sample-stack-with-hooks'
        },
        'parameters': {
            'InstanceType': 't2.medium'
        }
    }
    assert config == exp_config
    assert parameters == [{'ParameterKey': 'InstanceType', 'ParameterValue': 't2.medium', 'UsePreviousValue': False}]

    assert stack_outputs[0]['OutputKey'] == 'BucketName'
    assert stack_outputs[0]['OutputValue'].startswith(
        'infra-dev-kumo-sample-stack-with-hooks-s3bucket1-')
    assert stack_state == 'CREATE_COMPLETE'


def post_update_hook():
    print("i'm a post update hook")


def post_create_hook():
    print("i'm a post create hook")


def get_stack_policy():
    return json.dumps({
          "Statement" : [
            {
              "Effect" : "Allow",
              "Action" : "Update:Modify",
              "Principal": "*",
              "Resource" : "*"
            },
            {
              "Effect" : "Deny",
              "Action" : ["Update:Replace", "Update:Delete"],
              "Principal": "*",
              "Resource" : "*"
            }
          ]
        })

"""
def get_stack_policy_during_update():
    return json.dumps({
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "Update:*",
                "Principal": "*",
                "Resource": "*"
            }
        ]
   })
"""
