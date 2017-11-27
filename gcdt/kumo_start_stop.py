# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from .gcdt_logging import getLogger
from .utils import all_pages
from .kumo_core import stack_exists

log = getLogger(__name__)


def _stop_ec2_instances(awsclient, ec2_instances, wait=True):
    """Helper to stop ec2 instances.
    By default it waits for instances to stop.

    :param awsclient:
    :param ec2_instances:
    :param wait: waits for instances to stop
    :return:
    """
    if len(ec2_instances) == 0:
        return
    client_ec2 = awsclient.get_client('ec2')

    # get running instances
    running_instances = all_pages(
        client_ec2.describe_instance_status,
        {
            'InstanceIds': ec2_instances,
            'Filters': [{
                'Name': 'instance-state-name',
                'Values': ['pending', 'running']
            }]
        },
        lambda r: [i['InstanceId'] for i in r.get('InstanceStatuses', [])],
    )

    if running_instances:
        log.info('Stopping EC2 instances: %s', running_instances)
        client_ec2.stop_instances(InstanceIds=running_instances)

        if wait:
            # wait for instances to stop
            waiter_inst_stopped = client_ec2.get_waiter('instance_stopped')
            waiter_inst_stopped.wait(InstanceIds=running_instances)


def _start_ec2_instances(awsclient, ec2_instances, wait=True):
    """Helper to start ec2 instances

    :param awsclient:
    :param ec2_instances:
    :param wait: waits for instances to start
    :return:
    """
    if len(ec2_instances) == 0:
        return
    client_ec2 = awsclient.get_client('ec2')

    # get stopped instances
    stopped_instances = all_pages(
        client_ec2.describe_instance_status,
        {
            'InstanceIds': ec2_instances,
            'Filters': [{
                'Name': 'instance-state-name',
                'Values': ['stopping', 'stopped']
            }],
            'IncludeAllInstances': True
        },
        lambda r: [i['InstanceId'] for i in r.get('InstanceStatuses', [])],
    )

    if stopped_instances:
        # start all stopped instances
        log.info('Starting EC2 instances: %s', stopped_instances)
        client_ec2.start_instances(InstanceIds=stopped_instances)

        if wait:
            # wait for instances to come up
            waiter_inst_running = client_ec2.get_waiter('instance_running')
            waiter_inst_running.wait(InstanceIds=stopped_instances)

            # wait for status checks
            waiter_status_ok = client_ec2.get_waiter('instance_status_ok')
            waiter_status_ok.wait(InstanceIds=stopped_instances)


def _filter_db_instances_by_status(awsclient, db_instances, status_list):
    """helper to select dbinstances.

    :param awsclient:
    :param db_instances:
    :param status_list:
    :return: list of db_instances that match the filter
    """
    client_rds = awsclient.get_client('rds')
    db_instances_with_status = []

    for db in db_instances:
        response = client_rds.describe_db_instances(
            DBInstanceIdentifier=db
        )
        for entry in response.get('DBInstances', []):
            if entry['DBInstanceStatus'] in status_list:
                db_instances_with_status.append(db)

    return db_instances_with_status


def _stop_ecs_services(awsclient, services, template, parameters, wait=True):
    """Helper to change desiredCount of ECS services to zero.
    By default it waits for this to complete.
    Docs here: http://docs.aws.amazon.com/cli/latest/reference/ecs/update-service.html

    :param awsclient:
    :param services:
    :param template: the cloudformation template
    :param parameters: the parameters used for the cloudformation template
    :param wait: waits for services to stop
    :return:
    """
    if len(services) == 0:
        return
    client_ecs = awsclient.get_client('ecs')

    for service in services:
        log.info('Resize ECS service \'%s\' to desiredCount=0',
                 service['LogicalResourceId'])
        cluster, desired_count = _get_service_cluster_desired_count(
            template, parameters, service['LogicalResourceId'])
        log.debug('cluster: %s' % cluster)
        response = client_ecs.update_service(
            cluster=cluster,
            service=service['PhysicalResourceId'],
            desiredCount=0
        )


def _start_ecs_services(awsclient, services, template, parameters, wait=True):
    """Helper to set desiredCount of ECS services back to its template value
    Docs here: http://docs.aws.amazon.com/cli/latest/reference/ecs/update-service.html

    :param awsclient:
    :param services:
    :param template: the cloudformation template
    :param parameters: the parameters used for the cloudformation template
    :param wait: waits for services to start
    :return:
    """
    if len(services) == 0:
        return
    client_ecs = awsclient.get_client('ecs')

    for service in services:
        # resize service back to its original desiredCount values
        log.info('Resize ECS service \'%s\' back to original desiredCount value',
                 service['LogicalResourceId'])
        cluster, desired_count = _get_service_cluster_desired_count(
            template, parameters, service['LogicalResourceId'])
        log.debug('cluster: %s' % cluster)
        log.debug('desired count: %d' % desired_count)
        response = client_ecs.update_service(
            cluster=cluster,
            service=service['PhysicalResourceId'],
            desiredCount=desired_count
        )


def stop_stack(awsclient, stack_name, use_suspend=False):
    """Stop an existing stack on AWS cloud.

    :param awsclient:
    :param stack_name:
    :param use_suspend: use suspend and resume on the autoscaling group
    :return: exit_code
    """
    exit_code = 0

    # check for DisableStop
    #disable_stop = conf.get('deployment', {}).get('DisableStop', False)
    #if disable_stop:
    #    log.warn('\'DisableStop\' is set - nothing to do!')
    #else:
    if not stack_exists(awsclient, stack_name):
        log.warn('Stack \'%s\' not deployed - nothing to do!', stack_name)
    else:
        client_cfn = awsclient.get_client('cloudformation')
        client_autoscaling = awsclient.get_client('autoscaling')
        client_rds = awsclient.get_client('rds')
        client_ec2 = awsclient.get_client('ec2')

        resources = all_pages(
            client_cfn.list_stack_resources,
            { 'StackName': stack_name },
            lambda r: r['StackResourceSummaries']
        )

        autoscaling_groups = [
            r for r in resources
            if r['ResourceType'] == 'AWS::AutoScaling::AutoScalingGroup'
        ]

        # lookup all types of scaling processes
        #    [Launch, Terminate, HealthCheck, ReplaceUnhealthy, AZRebalance
        #     AlarmNotification, ScheduledActions, AddToLoadBalancer]
        response = client_autoscaling.describe_scaling_process_types()
        scaling_process_types = [t['ProcessName'] for t in response.get('Processes', [])]

        for asg in autoscaling_groups:
            # find instances in autoscaling group
            ec2_instances = all_pages(
                client_autoscaling.describe_auto_scaling_instances,
                {},
                lambda r: [i['InstanceId'] for i in r.get('AutoScalingInstances', [])
                           if i['AutoScalingGroupName'] == asg['PhysicalResourceId']],
            )

            if use_suspend:
                # alternative implementation to speed up start
                # only problem is that instances must survive stop & start
                # suspend all autoscaling processes
                log.info('Suspending all autoscaling processes for \'%s\'',
                         asg['LogicalResourceId'])
                response = client_autoscaling.suspend_processes(
                    AutoScalingGroupName=asg['PhysicalResourceId'],
                    ScalingProcesses=scaling_process_types
                )

                _stop_ec2_instances(awsclient, ec2_instances)
            else:
                # resize autoscaling group (min, max = 0)
                log.info('Resize autoscaling group \'%s\' to minSize=0, maxSize=0',
                         asg['LogicalResourceId'])
                response = client_autoscaling.update_auto_scaling_group(
                    AutoScalingGroupName=asg['PhysicalResourceId'],
                    MinSize=0,
                    MaxSize=0
                )
                if ec2_instances:
                    running_instances = all_pages(
                        client_ec2.describe_instance_status,
                        {
                            'InstanceIds': ec2_instances,
                            'Filters': [{
                                'Name': 'instance-state-name',
                                'Values': ['pending', 'running']
                            }]
                        },
                        lambda r: [i['InstanceId'] for i in r.get('InstanceStatuses', [])],
                    )
                    if running_instances:
                        # wait for instances to terminate
                        waiter_inst_terminated = client_ec2.get_waiter('instance_terminated')
                        waiter_inst_terminated.wait(InstanceIds=running_instances)

        # setting ECS desiredCount to zero
        services = [
            r for r in resources
            if r['ResourceType'] == 'AWS::ECS::Service'
        ]
        if services:
            template, parameters = _get_template_parameters(awsclient, stack_name)
            _stop_ecs_services(awsclient, services, template, parameters)

        # stopping ec2 instances
        instances = [
            r['PhysicalResourceId'] for r in resources
            if r['ResourceType'] == 'AWS::EC2::Instance'
        ]
        _stop_ec2_instances(awsclient, instances)

        # stopping db instances
        db_instances = [
            r['PhysicalResourceId'] for r in resources
            if r['ResourceType'] == 'AWS::RDS::DBInstance'
        ]
        running_db_instances = _filter_db_instances_by_status(
            awsclient, db_instances, ['available']
        )
        for db in running_db_instances:
            log.info('Stopping RDS instance \'%s\'', db)
            client_rds.stop_db_instance(DBInstanceIdentifier=db)

    return exit_code


def _get_autoscaling_min_max(template, parameters, asg_name):
    """Helper to extract the configured MinSize, MaxSize attributes from the
    template.

    :param template: cloudformation template (json)
    :param parameters: list of {'ParameterKey': 'x1', 'ParameterValue': 'y1'}
    :param asg_name: logical resource name of the autoscaling group
    :return: MinSize, MaxSize
    """
    params = {e['ParameterKey']: e['ParameterValue'] for e in parameters}
    asg = template.get('Resources', {}).get(asg_name, None)
    if asg:
        assert asg['Type'] == 'AWS::AutoScaling::AutoScalingGroup'
        min = asg.get('Properties', {}).get('MinSize', None)
        max = asg.get('Properties', {}).get('MaxSize', None)
        if 'Ref' in min:
            min = params.get(min['Ref'], None)
        if 'Ref' in max:
            max = params.get(max['Ref'], None)
        if min and max:
            return int(min), int(max)


def _get_service_cluster_desired_count(template, parameters, service_name):
    """Helper to extract the configured desiredCount attribute from the
    template.

    :param template: cloudformation template (json)
    :param parameters: list of {'ParameterKey': 'x1', 'ParameterValue': 'y1'}
    :param service_name: logical resource name of the ECS service
    :return: cluster, desiredCount
    """
    params = {e['ParameterKey']: e['ParameterValue'] for e in parameters}
    service = template.get('Resources', {}).get(service_name, None)
    if service:
        assert service['Type'] == 'AWS::ECS::Service'
        cluster = service.get('Properties', {}).get('Cluster', None)
        desired_count = service.get('Properties', {}).get('DesiredCount', None)
        if 'Ref' in cluster:
            cluster = params.get(cluster['Ref'], None)
        if not isinstance(desired_count, int) and 'Ref' in desired_count:
            desired_count = params.get(desired_count['Ref'], None)
        return cluster, int(desired_count)


def _get_template_parameters(awsclient, stack_name):
        # get template and parameters from cloudformation
        client_cfn = awsclient.get_client('cloudformation')
        response = client_cfn.get_template(
            StackName=stack_name,
            TemplateStage='Processed'
        )
        template = response.get('TemplateBody', {})
        response = client_cfn.describe_stacks(
            StackName=stack_name
        )

        parameters = response['Stacks'][0].get('Parameters', {})
        return template, parameters


def start_stack(awsclient, stack_name, use_suspend=False):
    """Start an existing stack on AWS cloud.

    :param awsclient:
    :param stack_name:
    :param use_suspend: use suspend and resume on the autoscaling group
    :return: exit_code
    """
    exit_code = 0

    # check for DisableStop
    #disable_stop = conf.get('deployment', {}).get('DisableStop', False)
    #if disable_stop:
    #    log.warn('\'DisableStop\' is set - nothing to do!')
    #else:
    if not stack_exists(awsclient, stack_name):
        log.warn('Stack \'%s\' not deployed - nothing to do!', stack_name)
    else:
        client_cfn = awsclient.get_client('cloudformation')
        client_autoscaling = awsclient.get_client('autoscaling')
        client_rds = awsclient.get_client('rds')

        resources = all_pages(
            client_cfn.list_stack_resources,
            { 'StackName': stack_name },
            lambda r: r['StackResourceSummaries']
        )

        autoscaling_groups = [
            r for r in resources
            if r['ResourceType'] == 'AWS::AutoScaling::AutoScalingGroup'
        ]

        # lookup all types of scaling processes
        #    [Launch, Terminate, HealthCheck, ReplaceUnhealthy, AZRebalance
        #     AlarmNotification, ScheduledActions, AddToLoadBalancer]
        response = client_autoscaling.describe_scaling_process_types()
        scaling_process_types = [t['ProcessName'] for t in response.get('Processes', [])]

        # starting db instances
        db_instances = [
            r['PhysicalResourceId'] for r in resources
            if r['ResourceType'] == 'AWS::RDS::DBInstance'
        ]
        stopped_db_instances = _filter_db_instances_by_status(
            awsclient, db_instances, ['stopped']
        )
        for db in stopped_db_instances:
            log.info('Starting RDS instance \'%s\'', db)
            client_rds.start_db_instance(DBInstanceIdentifier=db)

        # wait for db instances to become available
        for db in stopped_db_instances:
            waiter_db_available = client_rds.get_waiter('db_instance_available')
            waiter_db_available.wait(DBInstanceIdentifier=db)

        # starting ec2 instances
        instances = [
            r['PhysicalResourceId'] for r in resources
            if r['ResourceType'] == 'AWS::EC2::Instance'
        ]
        _start_ec2_instances(awsclient, instances)

        services = [
            r for r in resources
            if r['ResourceType'] == 'AWS::ECS::Service'
        ]

        if (autoscaling_groups and not use_suspend) or services:
            template, parameters = _get_template_parameters(awsclient, stack_name)

        # setting ECS desiredCount back
        if services:
            _start_ecs_services(awsclient, services, template, parameters)

        for asg in autoscaling_groups:
            if use_suspend:
                # alternative implementation to speed up start
                # only problem is that instances must survive stop & start
                # find instances in autoscaling group
                instances = all_pages(
                    client_autoscaling.describe_auto_scaling_instances,
                    {},
                    lambda r: [i['InstanceId'] for i in r.get('AutoScalingInstances', [])
                               if i['AutoScalingGroupName'] == asg['PhysicalResourceId']],
                )
                _start_ec2_instances(awsclient, instances)

                # resume all autoscaling processes
                log.info('Resuming all autoscaling processes for \'%s\'',
                         asg['LogicalResourceId'])
                response = client_autoscaling.resume_processes(
                    AutoScalingGroupName=asg['PhysicalResourceId'],
                    ScalingProcesses=scaling_process_types
                )
            else:
                # resize autoscaling group back to its original values
                log.info('Resize autoscaling group \'%s\' back to original values',
                         asg['LogicalResourceId'])
                min, max = _get_autoscaling_min_max(
                    template, parameters, asg['LogicalResourceId'])
                response = client_autoscaling.update_auto_scaling_group(
                    AutoScalingGroupName=asg['PhysicalResourceId'],
                    MinSize=min,
                    MaxSize=max
                )

    return exit_code
