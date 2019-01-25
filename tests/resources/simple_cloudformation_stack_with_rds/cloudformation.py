#!/usr/bin/env python

# Converted from RDS template located at:
# https://github.com/cloudtools/troposphere/blob/master/examples/RDS_with_DBParameterGroup.py
import troposphere
from troposphere import Parameter, Output, Ref, Template
from troposphere.rds import DBInstance, DBParameterGroup
from troposphere.ec2 import SecurityGroupRule as SGR


t = Template()

t.add_description(
    "AWS CloudFormation Sample Template S3_Bucket: template showing "
    "how to create a publicly accessible S3 bucket."
)

param_vpc_id = t.add_parameter(Parameter(
    'VPCId',
    Type="String",
    Description="ID of glomex default VPC",
))

param_rds_subnet_group = t.add_parameter(Parameter(
    'RDSSubnetGroupName',
    Type="String",
    Description="Name of DB Subnet Group",
))


dbuser = t.add_parameter(Parameter(
    "DBUser",
    Description="The database admin account username",
    Type="String",
    MinLength="1",
    MaxLength="16",
    AllowedPattern="[a-zA-Z][a-zA-Z0-9]*",
    ConstraintDescription=("must begin with a letter and contain only"
                           " alphanumeric characters.")
))

dbpassword = t.add_parameter(Parameter(
    "DBPassword",
    NoEcho=True,
    Description="The database admin account password",
    Type="String",
    MinLength="1",
    MaxLength="41",
    AllowedPattern="[a-zA-Z0-9]*",
    ConstraintDescription="must contain only alphanumeric characters."
))


myrdsparamgroup = t.add_resource(DBParameterGroup(
    "MyRDSParamGroup",
    Family="MySQL5.5",
    Description="CloudFormation Sample Database Parameter Group",
    Parameters={
        "autocommit": "1",
        "general_log": "1",
        "old_passwords": "0"
    }
))


# Allow access from VPN
#
sg_frontend_db = troposphere.ec2.SecurityGroup(
    'infraDevUnittestSampleRDSsg',
    GroupDescription="infraDevDataBaseSecurityGroup",
    VpcId=Ref(param_vpc_id),
    #SecurityGroupIngress=sgs,
)
t.add_resource(sg_frontend_db)


mydb = t.add_resource(DBInstance(
    "infraDevUnittestSampleRDS",
    AllocatedStorage="5",
    DBInstanceClass="db.m1.small",
    Engine="MySQL",
    EngineVersion="5.5",
    MasterUsername=Ref(dbuser),
    MasterUserPassword=Ref(dbpassword),
    DBParameterGroupName=Ref(myrdsparamgroup),
    VPCSecurityGroups=[Ref(sg_frontend_db)],
    DBSubnetGroupName=Ref(param_rds_subnet_group),
))


def generate_template():
    return t.to_json()
