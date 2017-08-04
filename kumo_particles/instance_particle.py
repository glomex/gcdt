# -*- coding: utf-8 -*-
"""reusable particles.
"""
from __future__ import unicode_literals, print_function

import troposphere
from troposphere import Parameter, Ref, Output, GetAtt, Join
from troposphere import Base64, Join, GetAtt, Output
from troposphere import autoscaling
from troposphere import elasticloadbalancing as elb
from troposphere.codedeploy import Application, DeploymentGroup
import troposphere.ec2
import troposphere.autoscaling
from troposphere.ec2 import SecurityGroupRule as SGR
import troposphere.s3
import troposphere.logs
import troposphere.autoscaling
import troposphere.ec2
import troposphere.logs
import troposphere.s3
import troposphere.sqs
#from troposphere.rds import DBInstance
from troposphere.autoscaling import AutoScalingGroup, MetricsCollection
from troposphere.autoscaling import LaunchConfiguration
from troposphere.cloudwatch import Alarm
from troposphere.cloudwatch import MetricDimension
from troposphere.iam import InstanceProfile
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
from troposphere.route53 import RecordSetType

from gcdt.iam import IAMRoleAndPolicies
# from glomex_utils import servicediscovery
from gcdt import servicediscovery
from gcdt.kumo_particle_helper import Particle


# private helpers
def _create_elastic_load_balancer(template,
                                  TemplateName='ElasticLoadBalancer',
                                  BalancerSecurityGroups=[],
                                  Scheme='internal',
                                  FancyDNSNameParts=[],
                                  FancyDNSHostedZone=[],
                                  #FancyDNSHostedZoneNew=[],
                                  FancyDNSOutputVariable='',
                                  WhitelistedIPs=[],
                                  WhitelistedSecurityGroups=[],
                                  HttpsOnly=False,
                                  CustomTags={},
                                  #DeprecateEC2Basics=False
                                  DefaultSubnetIds=None
                                  ):
    # Configuring security groups
    sgi = []

    if len(WhitelistedIPs) > 0:
        for ip in WhitelistedIPs:
            if (not HttpsOnly):
                sgi.append(
                    SGR(CidrIp=ip, FromPort=80, ToPort=80, IpProtocol='tcp'))
            sgi.append(
                SGR(CidrIp=ip, FromPort=443, ToPort=443, IpProtocol='tcp'))

    if len(WhitelistedSecurityGroups) > 0:
        for sg in WhitelistedSecurityGroups:
            if (not HttpsOnly):
                sgi.append(SGR(SourceSecurityGroupId=sg, FromPort=80, ToPort=80,
                               IpProtocol='tcp'))
            sgi.append(SGR(SourceSecurityGroupId=sg, FromPort=443, ToPort=443,
                           IpProtocol='tcp'))

    Listeners = [
        elb.Listener(
            LoadBalancerPort="443",
            InstancePort="80",
            Protocol="HTTPS",
            InstanceProtocol="HTTP",
            # TODO make this configurable
            SSLCertificateId=Join("", [
                "arn:aws:iam::",
                Ref('AWS::AccountId'),
                ':server-certificate/cloudfront/multidomain.glomex.cloud-2016-8-30'
            ])
        )
    ]

    if (not HttpsOnly):
        Listeners.append(elb.Listener(LoadBalancerPort="80", InstancePort="80",
                                      Protocol="HTTP"))

    # Creating balancer
    '''
    if (DeprecateEC2Basics):
        try:
            param_vpc_id = template.add_parameter(troposphere.Parameter(
                'VPCId',
                Description='The glomex default vpc id DefaultVPCId',
                Type='String'
            ))
            ref_vpc_id = Ref(param_vpc_id)
        except ValueError:
            ref_vpc_id = Ref('VPCId')

        security_group = template.add_resource(troposphere.ec2.SecurityGroup(
            '%s%sSG' % (template.SERVICE_NAME, TemplateName),
            GroupDescription="%sLoadBalancerSecurityGroup" % template.SERVICE_NAME,
            VpcId=ref_vpc_id,
            SecurityGroupIngress=sgi,
            Tags=template.DEFAULT_TAGS + troposphere.Tags(**CustomTags)
        ))

        try:
            param_subnet_ids = template.add_parameter(troposphere.Parameter(
                'DefaultSubnetIds',
                Description='A pseudo comma separated list of subnet ids in the VPC which should be used',
                Type='CommaDelimitedList'
            ))
            subnet_param = Ref(param_subnet_ids)
        except ValueError:
            subnet_param = Ref('DefaultSubnetIds')
    else:
    '''
    security_group = template.add_resource(troposphere.ec2.SecurityGroup(
        '%s%sSG' % (template.SERVICE_NAME, TemplateName),
        GroupDescription="%sLoadBalancerSecurityGroup" % template.SERVICE_NAME,
        #VpcId=GetAtt('EC2Basics', 'vpcid'),
        SecurityGroupIngress=sgi,
        Tags=template.DEFAULT_TAGS + troposphere.Tags(**CustomTags)
    ))

    #subnet_param = GetAtt('EC2Basics', 'subnet_ids')

    BalancerSecurityGroups.append(Ref(security_group))

    elastic_load_balancer = template.add_resource(elb.LoadBalancer(
        TemplateName,
        ConnectionDrainingPolicy=elb.ConnectionDrainingPolicy(
            Enabled=True,
            Timeout=300,
        ),
        CrossZone=True,
        Scheme=Scheme,
        Subnets=DefaultSubnetIds,
        Listeners=Listeners,
        HealthCheck=elb.HealthCheck(
            Target=Join("", ["HTTP:", "80", "/release"]),
            # TODO modify for proper checking endpoint, add parameter
            HealthyThreshold="3",
            UnhealthyThreshold="5",
            Interval="25",
            Timeout="15",
        ),
        SecurityGroups=BalancerSecurityGroups,
        Tags=template.DEFAULT_TAGS + troposphere.Tags(**CustomTags)
    ))

    # Adding fancy name
    if len(FancyDNSNameParts) > 0:
        fancy_dns_record = _create_elastic_load_balancer_fancy_dns(
            template, elastic_load_balancer,
            TemplateName=TemplateName + "DNSRecord",
            FancyDNSParts=FancyDNSNameParts,
            HostedZone=FancyDNSHostedZone
        )
        #if FancyDNSHostedZoneNew:
        #    fancy_dns_record = _create_elastic_load_balancer_fancy_dns(
        #        template, elastic_load_balancer,
        #        TemplateName=TemplateName + "DNSRecordNew",
        #        FancyDNSParts=FancyDNSNameParts,
        #        HostedZone=FancyDNSHostedZoneNew
        #    )

        if FancyDNSOutputVariable == '':
            FancyDNSOutputVariable = TemplateName + 'DNSRecord'

        # self.output(FancyDNSOutputVariable, Ref(fancy_dns_record),
        #            'fancy name of %s' % TemplateName)
        template.add_output(
            Output(FancyDNSOutputVariable,
                   Description='fancy name of %s' % TemplateName,
                   Value=Ref(fancy_dns_record)
                   )
        )

    return elastic_load_balancer, security_group


def _create_elastic_load_balancer_fancy_dns(template,
                                            Balancer,
                                            TemplateName="ELBDNSRecord",
                                            FancyDNSParts=[],
                                            HostedZone=[]):
    ELBDNSRecord = template.add_resource(RecordSetType(
        TemplateName,
        HostedZoneName=Join("", [HostedZone, "."]),
        Comment="fancy CNAME to the elastic LoadBalancer",
        Name=Join("", FancyDNSParts + [".", HostedZone, "."]),
        Type="CNAME",
        TTL="900",
        ResourceRecords=[GetAtt(Balancer, 'DNSName')]
    ))

    return ELBDNSRecord


def _create_autoscaling_group(template,
                              LaunchConfig,
                              AutoscalingGroupName="AutoscalingGroup",
                              LoadBalancers=[],
                              MinSize=1,
                              MaxSize=5,
                              #DeprecateEC2Basics=False
                              VpcId=None
                              ):
    #if (DeprecateEC2Basics):
    #    try:
    #        param_subnet_ids = template.add_parameter(troposphere.Parameter(
    #            'DefaultSubnetIds',
    #            Description='A pseudo comma separated list of subnet ids in the VPC which should be used',
    #            Type='CommaDelimitedList'
    #        ))
    #        subnet_param = Ref(param_subnet_ids)
    #    except ValueError:
    #        subnet_param = Ref('DefaultSubnetIds')
    #else:
    #    subnet_param = GetAtt('EC2Basics', 'subnet_ids')

    # TODO: change rolling update config
    return template.add_resource(AutoScalingGroup(
        AutoscalingGroupName,
        LaunchConfigurationName=LaunchConfig,
        MinSize=MinSize,
        MaxSize=MaxSize,
        VPCZoneIdentifier=VpcId,
        HealthCheckType="ELB",
        HealthCheckGracePeriod=300,
        LoadBalancerNames=LoadBalancers,
        UpdatePolicy=UpdatePolicy(
            AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                PauseTime='PT2M',
                MinInstancesInService="1",
                MaxBatchSize='5',
                WaitOnResourceSignals=False
            )
        ),
        MetricsCollection=[
            MetricsCollection(
                Granularity="1Minute",
                Metrics=[
                    "GroupMinSize",
                    "GroupMaxSize",
                    "GroupDesiredCapacity",
                    "GroupInServiceInstances",
                    "GroupPendingInstances",
                    "GroupStandbyInstances",
                    "GroupTerminatingInstances",
                    "GroupTotalInstances"
                ]
            )],
        Tags=troposphere.autoscaling.Tags(**{
            'Name': ['Service-%s-frontend' % template.SERVICE_NAME, True],
            # Do not use from self.defaultTags. Should be refactored
            'service-name': [template.SERVICE_NAME, True],
            'environment': [template.SERVICE_ENVIRONMENT, True],
        })
    ))


def _create_autoscaling_cpu_alarm(template,
                                  AutoScalingGroup,
                                  PolicyName="ScaleUp",
                                  AlarmName="CpuHighAlarm",
                                  ThresholdPeriod="180",
                                  CooldownPeriod="60",
                                  CpuThreshold="50",
                                  ScalingAdjustment="3",
                                  ComparisonOperator="GreaterThanThreshold"
                                  ):
    ScalingUpPolicy = template.add_resource(autoscaling.ScalingPolicy(
        PolicyName,
        AdjustmentType="ChangeInCapacity",
        AutoScalingGroupName=AutoScalingGroup,
        Cooldown=CooldownPeriod,
        ScalingAdjustment=ScalingAdjustment,

    ))

    CpuAlarm = template.add_resource(
        Alarm(
            AlarmName,
            AlarmDescription=
            "%s util, %s if CPU %s %s for %s seconds" % (
                AlarmName, PolicyName, ComparisonOperator, CpuThreshold,
                ThresholdPeriod),
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[
                MetricDimension(
                    Name="AutoScalingGroupName",
                    Value=AutoScalingGroup
                ),
            ],
            Statistic="Maximum",
            Period=ThresholdPeriod,
            EvaluationPeriods="1",
            Threshold=CpuThreshold,
            ComparisonOperator=ComparisonOperator,
            AlarmActions=[Ref(ScalingUpPolicy)]
        )
    )

    return CpuAlarm


def _create_launch_configuration(
        template,
        InstanceType,
        InstanceRoleProfile,
        InstanceSecurityGroups=[],
        LaunchParameters=[],
        TemplateName="LaunchConfiguration",
        AmiId=None,
        OrgTeam=None
    ):
    launch_script_lines = [
        "echo glomex_dp > /etc/puppet_role\n",
        "mkdir -p /etc/glomex/hiera\n",
        "ln -sf /usr/bin/pip-2.7 /usr/bin/pip\n",
        "/usr/local/bin/pubkeysync org_team_ops %s\n" % OrgTeam
    ]

    ImageId = AmiId  # if AmiId is not None else servicediscovery.get_base_ami()

    if LaunchParameters:
        for key, value in LaunchParameters.iteritems():
            launch_script_lines.append("echo %s: " % key)
            launch_script_lines.append(value)
            launch_script_lines.append(
                " >> /etc/glomex/hiera/cloudformation.yaml\n")

    launch_config = template.add_resource(LaunchConfiguration(
        TemplateName,
        UserData=Base64(Join('', [
            "#!/bin/bash\n",
            {
                "Fn::Join": ["", launch_script_lines]
            },
        ])),
        ImageId=ImageId,
        IamInstanceProfile=InstanceRoleProfile,
        SecurityGroups=InstanceSecurityGroups,
        InstanceType=InstanceType,
        BlockDeviceMappings=[
            troposphere.ec2.BlockDeviceMapping(
                Ebs=troposphere.ec2.EBSBlockDevice(
                    DeleteOnTermination=True,
                    # TODO make this configurable
                    VolumeSize=16,
                    VolumeType='gp2'
                ),
                DeviceName='/dev/xvda')
        ]

    ))

    return launch_config


def _create_role_codedeploy_trust(template):
    # Instantiate helper
    iam = IAMRoleAndPolicies(template, 'codedeploy-',
                             ["codedeploy.us-east-1.amazonaws.com",
                              "codedeploy.us-west-2.amazonaws.com",
                              "codedeploy.eu-west-1.amazonaws.com",
                              "codedeploy.ap-southeast-2.amazonaws.com"], '/')

    """
     "CodeDeployTrustRole": {
         "Type": "AWS::IAM::Role",
         "Properties": {
           "AssumeRolePolicyDocument": {
             "Statement": [
               {
                 "Sid": "1",
                 "Effect": "Allow",
                 "Principal": {
                   "Service": [
                     "codedeploy.us-east-1.amazonaws.com",
                     "codedeploy.us-west-2.amazonaws.com",
                     "codedeploy.eu-west-1.amazonaws.com",
                     "codedeploy.ap-southeast-2.amazonaws.com"
                   ]
                 },
                 "Action": "sts:AssumeRole"
               }
             ]
           },
           "Path": "/"
         }
       },
    """

    role_name = "CodeDeployTrustRole"
    role_code_deploy_trust_role = iam.build_role(
        role_name
    )

    """
    "CodeDeployRolePolicies": {
      "Type": "AWS::IAM::Policy",
      "Properties": {
        "PolicyName": "CodeDeployPolicy",
        "PolicyDocument": {
          "Statement": [
            {
              "Effect": "Allow",
              "Resource": [
                "*"
              ],
              "Action": [
                "ec2:Describe*"
              ]
            },
            {
              "Effect": "Allow",
              "Resource": [
                "*"
              ],
              "Action": [
                "autoscaling:CompleteLifecycleAction",
                "autoscaling:DeleteLifecycleHook",
                "autoscaling:DescribeLifecycleHooks",
                "autoscaling:DescribeAutoScalingGroups",
                "autoscaling:PutLifecycleHook",
                "autoscaling:RecordLifecycleActionHeartbeat"
              ]
            }
          ]
        },
        "Roles": [
          {
            "Ref": "CodeDeployTrustRole"
          }
        ]
      }
    },
    """
    CodeDeployPolicyName = "CodeDeployRolePolicies"
    CodeDeployRolePolicies = iam.build_policy(
        CodeDeployPolicyName,
        [
            {
                "Effect": "Allow",
                "Resource": [
                    "*"
                ],
                "Action": [
                    "ec2:Describe*"
                ]
            },
            {
                "Effect": "Allow",
                "Resource": [
                    "*"
                ],
                "Action": [
                    "autoscaling:CompleteLifecycleAction",
                    "autoscaling:DeleteLifecycleHook",
                    "autoscaling:DescribeLifecycleHooks",
                    "autoscaling:DescribeAutoScalingGroups",
                    "autoscaling:PutLifecycleHook",
                    "autoscaling:RecordLifecycleActionHeartbeat"
                ]
            }
        ],
        [
            Ref(role_code_deploy_trust_role)
        ]
    )

    """
        "InstanceRole": {
          "Type": "AWS::IAM::Role",
          "Properties": {
            "AssumeRolePolicyDocument": {
              "Statement": [
                {
                  "Effect": "Allow",
                  "Principal": {
                    "Service": [
                      "ec2.amazonaws.com"
                    ]
                  },
                  "Action": [
                    "sts:AssumeRole"
                  ]
                }
              ]
            },
            "Path": "/"
          }
        },
    """

    return role_code_deploy_trust_role


def _create_role_cms_instance(template, BasePermissions, ExtraPermissions=None):
    if ExtraPermissions is None:
        ExtraPermissions = []
    # Instantiate helper
    iam = IAMRoleAndPolicies(template, 'instance-role-',
                             ['ec2.amazonaws.com'], '/ec2/')

    role_name = "%s-instance-role" % template.SERVICE_NAME
    role_mep_cms_instance_role = iam.build_role(
        role_name, [Ref(BasePermissions)]
    )

    base_permissions = [
        {
            "Effect": "Allow",
            "Action": [
                "autoscaling:Describe*",
                "autoscaling:UpdateAutoScalingGroup",
                "autoscaling:EnterStandby",
                "autoscaling:ExitStandby",
                "cloudformation:Describe*",
                "cloudformation:GetTemplate",
                "s3:Get*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Resource": [
                "arn:aws:logs:*:*:*"
            ],
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "autoscaling:*",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "elasticloadbalancing:*",
            "Resource": "*"
        }
    ]

    role_name = "InstanceRolePolicies"
    InstanceRolePolicies = iam.build_policy(
        role_name,
        base_permissions + ExtraPermissions,
        [
            Ref(role_mep_cms_instance_role)
        ]
    )

    """
        "InstanceRoleInstanceProfile": {
          "Type": "AWS::IAM::InstanceProfile",
          "Properties": {
            "Path": "/",
            "Roles": [
              {
                "Ref": "InstanceRole"
              }
            ]
          }
        },
    """

    return role_mep_cms_instance_role


def _create_instance_profile(
        template,
        InstanceRolePrefix="InstanceRoleMepCms",
        Roles=[]
):
    return template.add_resource(InstanceProfile(
        InstanceRolePrefix + template.SERVICE_NAME,
        Roles=Roles
    ))


################# reusable particles ######################################
def create_instance(template, ExtraPermissions=None):
    """Training / Demo - Particle to create an instance with autoscaling,
    deployment, and elbs.

    :param template:
    :param ExtraPermissions:
    :return:
    """
    ################# Parameter Section ######################################
    #param_hosted_zone_new = template.add_parameter(troposphere.Parameter(
    #    'HostedZoneNew',
    #    Description='New name of the hosted Zone (without trailing dot)',
    #    Type='String'
    #))

    param_hosted_zone = template.add_parameter(troposphere.Parameter(
        'HostedZone',
        Description='Name of the hosted Zone (without trailing dot)',
        Type='String'
    ))

    param_elb_dns = template.add_parameter(troposphere.Parameter(
        'ELBDNSName',
        Description='Host part of the Elastic Loadbalancer which is used for the fancy hostname. The name of the hosted zone shall not be included',
        Type='String',
        ConstraintDescription="must comply the following schema (excluding the domain part): <projekt>-<funktion><counter|instance-id>-<stage>[-<region>][-int|-ext].[mep|mdp|vvp|dp|infra].glomex.cloud For example adpxy-elb"
    ))

    #param_deployment_config = template.add_parameter(Parameter(
    #    "DeploymentConfig",
    #    Description="Shared deployment config",
    #    Type="String",
    #))

    param_instance_policy_arn = template.add_parameter(troposphere.Parameter(
        'DefaultInstancePolicyARN',
        Description='A base policys ARN you could attach to all of your instances when required. This handles several default use cases.',
        Type='String'
    ))

    param_scale_min_capacity = template.add_parameter(troposphere.Parameter(
        'ScaleMinCapacity',
        Default="1",
        Type="String",
        Description="Number of api servers to run",
    ))

    param_scale_max_capacity = template.add_parameter(troposphere.Parameter(
        'ScaleMaxCapacity',
        Default="5",
        Type="String",
        Description="Number of api servers to run",
    ))

    param_instance_type = template.add_parameter(troposphere.Parameter(
        'InstanceType',
        Description='Type of EC2 instance',
        Type='String',
        Default='t2.micro',
    ))

    #param_alarm_email = template.add_parameter(troposphere.Parameter(
    #    'AlarmEmail',
    #    Description='The email address alarms should be sent to',
    #    Type='String',
    #))

    param_base_ami = template.add_parameter(troposphere.Parameter(
        'BaseAMIID',
        Description='base ami id or lookup that should return id',
        Type='String'
    ))

    param_org_team = template.add_parameter(troposphere.Parameter(
        'OrgTeam',
        Description='org team with ssh access to the ec2 instances',
        Type='String',
        Default=''
    ))

    param_default_subnet_ids = template.add_parameter(troposphere.Parameter(
        'DefaultSubnetIds',
        Description='comma sep. list of subnet ids',
        Type='String',
    ))

    param_vpc_id = template.add_parameter(troposphere.Parameter(
        'VPCId',
        Description='vpc id',
        Type='String',
    ))

    #param_vpn_sg_id = template.add_parameter(troposphere.Parameter(
    #    'EC2SecuritySSHPlusServerOpenVPN',
    #    Description='ID of security group that allows access via VPN',
    #    Type='String'
    #))

    ################# ELB Section ########################
    elasticLB, sg_frontend_elb = _create_elastic_load_balancer(
        template,
        Scheme='internet-facing',
        WhitelistedIPs=['0.0.0.0/0'],
        FancyDNSNameParts=[Ref(param_elb_dns), "-", Ref("AWS::Region")],
        FancyDNSHostedZone=Ref(param_hosted_zone),
        #FancyDNSHostedZoneNew=Ref(param_hosted_zone_new),
        HttpsOnly=True,
        DefaultSubnetIds=Ref(param_default_subnet_ids)
        #DeprecateEC2Basics=True
    )

    internalElasticLB, sg_internal_elb = _create_elastic_load_balancer(
        template,
        TemplateName='InternalLoadBalancer',
        Scheme='internal',
        WhitelistedIPs=['192.168.225.0/24'],
        #WhitelistedSecurityGroups=[Ref(param_microservices_access_sg)],
        FancyDNSNameParts=[Ref(param_elb_dns), "-internal-",
                           Ref("AWS::Region")],
        FancyDNSHostedZone=Ref(param_hosted_zone),
        #FancyDNSHostedZoneNew=Ref(param_hosted_zone_new)
        #DeprecateEC2Basics=True
        DefaultSubnetIds=Ref(param_default_subnet_ids)
    )

    ### sg
    sg_frontend_web = troposphere.ec2.SecurityGroup(
        '%sFrontendWeb' % template.SERVICE_NAME,
        GroupDescription="%sWebServerSecurityGroup" % template.SERVICE_NAME,
        #VpcId=Ref('VPCId'),
        VpcId=Ref(param_vpc_id),
        SecurityGroupIngress=[
            SGR(SourceSecurityGroupId=Ref(sg_frontend_elb), FromPort=80,
                ToPort=80, IpProtocol='tcp'),
            SGR(SourceSecurityGroupId=Ref(sg_internal_elb), FromPort=80,
                ToPort=80, IpProtocol='tcp'),
        ],
        )
    template.add_resource(sg_frontend_web)

    ################# LaunchConfiguration Section ############################
    # Security group to attach to instance

    instance_role_profile = _create_instance_profile(
        template,
        Roles=[
            Ref(_create_role_cms_instance(
                template,
                param_instance_policy_arn,
                # ExtraPermissions=[s3_permissions, sqs_permissions, sns_permissions, eventbus_permissions]
                ExtraPermissions=ExtraPermissions
            ))
        ]
    )

    # we said to use settings.json or stack_output.yaml for that
    '''
    # DO NOT add another cronjob without changing shutdown_cron.sh!
    launch_params = {
        "db::host": GetAtt(db, "Endpoint.Address"),
        "notify::alarm::email": {"Ref": "AlarmEmail"},
        "db::name": {"Ref": "DBName"},
        "db::user": {"Ref": "DBUser"},
        "db::pass": {"Ref": "DBPassword"},
        "mep::portal::s3::import_bucket": Ref(s3_bucket),
        "mep::portal::sns::topic_name": {"Ref": "SNSAlertsTopic"},
        "mep::portal::sqs::queue_name": GetAtt(sqs_queue, 'QueueName'),
        "mep::portal::notifier::url": {"Ref": "NotifierEndpoint"},
        "mep::portal::notifier::key": {"Ref": "NotifierKey"},
        "mep::portal::ims::host": {"Ref": "MesImageServiceHost"},
        "mep::portal::relation_service::host": {"Ref": "MesRelationServiceHost"},
        "mep::portal::license_profile_service::host": {"Ref": "MesLicenseProfileServiceHost"},
        "mep::portal::global_taxonomy_service::host": {"Ref": "MesGlobalTaxonomyServiceHost"},
        "mep::portal::lookup_service::host" : {"Ref": "MesLookupServiceHost"},
        "mep::portal::tenant_service::host" : {"Ref": "MesTenantServiceHost"},
        "mep::portal::environment": {"Ref": "StackEnvironment"},
        "logstash::host": Ref(param_logstash_host),
        "mes::eventbus::topic_arn": Ref(eventbus_topic),
    }
    '''

    launch_config = _create_launch_configuration(
        template,
        InstanceType=Ref(param_instance_type),
        InstanceRoleProfile=Ref(instance_role_profile),
        InstanceSecurityGroups=[
            Ref(sg_frontend_web),
            #Ref(param_vpn_sg_id),
            #Ref(param_microservices_access_sg)
        ],
        # LaunchParameters=launch_params,
        AmiId=Ref(param_base_ami),
        OrgTeam=Ref(param_org_team)
    )

    ################# AutoScalingGroup Section ###############################
    AutoScalingGroup = _create_autoscaling_group(
        template,
        LaunchConfig=Ref(launch_config),
        LoadBalancers=[Ref(elasticLB), Ref(internalElasticLB)],
        MinSize=Ref(param_scale_min_capacity),
        MaxSize=Ref(param_scale_max_capacity),
        #DeprecateEC2Basics=True
        VpcId=Ref(param_vpc_id)
    )

    ################# Cpu Alarm ##############################################
    CpuAlarmHigh = _create_autoscaling_cpu_alarm(
        template,
        Ref(AutoScalingGroup),
        PolicyName="ScaleUp",
        AlarmName="CpuHighAlarm",
        ThresholdPeriod="60",
        CooldownPeriod="60",
        CpuThreshold="40",
        ScalingAdjustment="3",
        ComparisonOperator="GreaterThanThreshold"
    )

    CpuAlarmLow = _create_autoscaling_cpu_alarm(
        template,
        Ref(AutoScalingGroup),
        PolicyName="ScaleDown",
        AlarmName="CpuLowAlarm",
        ThresholdPeriod="300",
        CooldownPeriod="180",
        CpuThreshold="10",
        ScalingAdjustment="-1",
        ComparisonOperator="LessThanThreshold"
    )

    ################# CodeDeploy ############################################
    role_code_deploy_trust_role = _create_role_codedeploy_trust(template)

    app = template.add_resource(
        Application('%sApplication' % template.SERVICE_NAME))

    template.add_output(
        Output('applicationName',
               Description='Name of the CodeDeploy application', Value=Ref(app))
    )

    ############### CreateDeploymentGroup using applicationName as input and deploymentConfigName ############
    depgroup = template.add_resource(DeploymentGroup(
        "%sDg" % template.SERVICE_NAME,
        ApplicationName=Ref(app),
        #DeploymentConfigName=Ref(param_deployment_config),
        DeploymentConfigName="CodeDeployDefaultTemplate.AllAtOnce%s" % template.SERVICE_NAME,
        AutoScalingGroups=[Ref(AutoScalingGroup)],
        ServiceRoleArn=GetAtt(role_code_deploy_trust_role, "Arn")
    ))

    template.add_output(
        Output('DeploymentGroup',
               Description='Name of the CodeDeploy deployment group',
               Value=Ref(depgroup))
    )

    return Particle(template,
                    [elasticLB, internalElasticLB, sg_frontend_web, app, depgroup],
                    None)
