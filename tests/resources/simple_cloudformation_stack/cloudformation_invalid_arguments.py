#!/usr/bin/env python

import troposphere

# Converted from S3_Bucket.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/
import json
from troposphere import Output, Ref, Template
from troposphere.s3 import Bucket, PublicRead
import sample_hook

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


def generate_template(invalid_context, invalid_config):
    # do not go beyond this point!
    assert False


def post_hook():
    sample_hook.post_hook()


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
