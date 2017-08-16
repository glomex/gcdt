#!/usr/bin/env python

# Converted from RDS template located at:
# https://github.com/cloudtools/troposphere/blob/master/examples/RDS_with_DBParameterGroup.py
import os
import troposphere
from troposphere import Base64, Join, Parameter, Output, Ref, Template, Tags
from troposphere.rds import DBInstance, DBParameterGroup
from troposphere.ec2 import SecurityGroupRule as SGR
from gcdt.iam import IAMRoleAndPolicies

SERVICE_NAME = os.getenv('SERVICE_NAME', 'gcdtSampleStackWithEc2Instance')

t = Template()

t.add_description(
    "AWS CloudFormation Sample Template S3_Bucket: template showing "
    "how to create a publicly accessible S3 bucket."
)

param_vpc_id = t.add_parameter(troposphere.Parameter(
    'VPCId',
    Type="String",
    Description="ID of glomex default VPC",
))

param_instance_type = t.add_parameter(troposphere.Parameter(
    'InstanceType',
    Description='Type of EC2 instance',
    Type='String',
    Default='t2.micro',
))

param_hosted_zone = t.add_parameter(troposphere.Parameter(
    'HostedZone',
    Description='Name of the hosted Zone (without trailing dot)',
    Type='String'
))


param_launch_subnet_id = t.add_parameter(troposphere.Parameter(
    'EC2SubnetId',
    Description='ID of the VPN access security group',
    Type='String',
))

param_instance_policy_arn = t.add_parameter(troposphere.Parameter(
    'DefaultInstancePolicyARN',
    Description='A base policys ARN you could attach to all of your instances when required. This handles several default use cases.',
    Type='String'
))

param_base_ami_id = t.add_parameter(troposphere.Parameter(
    'BaseAMIID',
    Description='The ami-id of the glomex base image',
    Type='String'
))

################# Security Groups Section ################################

sg_ec2_instance = troposphere.ec2.SecurityGroup(
    '%sFrontendEC2' % SERVICE_NAME,
    GroupDescription="%sEC2SecurityGroup" % SERVICE_NAME,
    VpcId=Ref(param_vpc_id),
    SecurityGroupIngress=[
        SGR(CidrIp='192.168.225.0/24', FromPort=80, ToPort=80, IpProtocol='tcp'),
        SGR(CidrIp='192.168.225.0/24', FromPort=443, ToPort=443, IpProtocol='tcp')
    ],
    )
t.add_resource(sg_ec2_instance)

# Instantiate helper
iam = IAMRoleAndPolicies(t, 'instance-role-',
                         ['ec2.amazonaws.com'], '/ec2/')

role_name = "infra-%s-instance" % SERVICE_NAME
role_infra_instance_role = iam.build_role(
    role_name, [Ref(param_instance_policy_arn)]
)

# instance profile_name
instance_role_profile = t.add_resource(troposphere.iam.InstanceProfile(
    "InstanceRoleinfraCms%s" % SERVICE_NAME,
    Roles=[
        troposphere.Ref(role_infra_instance_role)
    ]
))



################# Instance Section ############################
EC2Instance = t.add_resource(troposphere.ec2.Instance(
    "EC2Instance",
    ImageId=Ref(param_base_ami_id),
    IamInstanceProfile=Ref(instance_role_profile),
    #SecurityGroupIds=[Ref(sg_ec2_instance), Ref(param_vpn_sg)],
    SecurityGroupIds=[Ref(sg_ec2_instance)],
    InstanceType=Ref(param_instance_type),
    BlockDeviceMappings=[
        troposphere.ec2.BlockDeviceMapping(
            Ebs=troposphere.ec2.EBSBlockDevice(
                DeleteOnTermination=True,
                VolumeSize=16,
                VolumeType='gp2'
            ),
            DeviceName='/dev/xvda')
    ],
    Tags=Tags(DeploymentGroup=SERVICE_NAME, Name=SERVICE_NAME),
    SubnetId=Ref(param_launch_subnet_id),
    AvailabilityZone='eu-west-1b'

))

t.add_output(Output('UsedBaseAMI', Description='ami ID of the given base image', Value=Ref(param_base_ami_id)))
################# End Instance Section ########################


def generate_template():
    return t.to_json()
