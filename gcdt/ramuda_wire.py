# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import json
import logging
import sys
import uuid

from botocore.exceptions import ClientError as ClientError
from clint.textui import colored

from gcdt.ramuda_utils import filter_bucket_notifications_with_arn
from gcdt.utils import json2table
from .ramuda_utils import lambda_exists, get_bucket_from_s3_arn, \
    get_rule_name_from_event_arn, create_aws_s3_arn, build_filter_rules, \
    list_of_dict_equals
from .s3 import bucket_exists
from . import event_source

PY3 = sys.version_info[0] >= 3

if PY3:
    unicode = str

log = logging.getLogger(__name__)
ALIAS_NAME = 'ACTIVE'


def _get_event_type(evt_source):
    """Get type of event e.g. 's3', 'events', 'kinesis',...

    :param evt_source:
    :return:
    """
    if 'schedule' in evt_source:
        return 'events'
    elif 'pattern' in evt_source:
        return 'events'
    else:
        arn = evt_source['arn']
        _, _, svc, _ = arn.split(':', 3)
        return svc


# event_source implementation from
# https://github.com/garnaat/kappa/tree/develop/kappa/event_source
# Note: we use a botocore compatible version of the kappa event_source functionality
# version from 2017-03-07, 46709b6
def wire(awsclient, events, lambda_name, alias_name=ALIAS_NAME):
    """Wiring a AWS Lambda function to events.
    Given a Lambda ARN, name and a list of events, schedule this as CloudWatch Events.

    'events' is a list of dictionaries, where the dict contains the string
    of the event 'schedule', and an optional 'name' and 'description'.

    'schedule' can be in rate or cron format:
        http://docs.aws.amazon.com/lambda/latest/dg/tutorial-scheduled-events-schedule-expressions.html

    :param awsclient:
    :param events: list of events
    :param lambda_name:
    :param alias_name:
    :return: exit_code
    """
    if not lambda_exists(awsclient, lambda_name):
        log.error(colored.red('The function you try to wire up doesn\'t ' +
                          'exist... Bailing out...'))
        return 1
    client_lambda = awsclient.get_client('lambda')
    lambda_function = client_lambda.get_function(FunctionName=lambda_name)
    lambda_arn = client_lambda.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']
    log.info('wiring lambda_arn %s ...' % lambda_arn)

    if lambda_function is not None:
        #_schedule_events(awsclient, events, lambda_arn)
        for event in events:
            evt_source = event['event_source']
            _add_event_source(awsclient, evt_source, lambda_arn)
    return 0


def _get_event_source_obj(awsclient, evt_source):
    """
    Given awsclient, event_source dictionary item
    create an event_source object of the appropriate event type
    to schedule this event, and return the object.
    """
    event_source_map = {
        'dynamodb': event_source.dynamodb_stream.DynamoDBStreamEventSource,
        'kinesis': event_source.kinesis.KinesisEventSource,
        's3': event_source.s3.S3EventSource,
        'sns': event_source.sns.SNSEventSource,
        'events': event_source.cloudwatch.CloudWatchEventSource,
        'cloudfront': event_source.cloudfront.CloudFrontEventSource
    }

    evt_type = _get_event_type(evt_source)
    event_source_func = event_source_map.get(evt_type, None)
    if not event_source:
        raise ValueError('Unknown event source: {0}'.format(
            evt_source['arn']))

    return event_source_func(awsclient, evt_source)


def _add_event_source(awsclient, evt_source, lambda_arn):
    """
    Given an event_source dictionary, create the object and add the event source.
    """
    event_source_obj = _get_event_source_obj(awsclient, evt_source)

    # (where zappa goes like remove, add)
    # we go with update and add like this:
    if event_source_obj.exists(lambda_arn):
        event_source_obj.update(lambda_arn)
    else:
        event_source_obj.add(lambda_arn)


def _remove_event_source(awsclient, evt_source, lambda_arn):
    """
    Given an event_source dictionary, create the object and remove the event source.
    """
    event_source_obj = _get_event_source_obj(awsclient, evt_source)
    if event_source_obj.exists(lambda_arn):
        event_source_obj.remove(lambda_arn)


def _get_event_source_status(awsclient, evt_source, lambda_arn):
    """
    Given an event_source dictionary, create the object and get the event source status.
    """
    event_source_obj = _get_event_source_obj(awsclient, evt_source)
    return event_source_obj.status(lambda_arn)


def unwire(awsclient, events, lambda_name, alias_name=ALIAS_NAME):
    """Unwire a list of event from an AWS Lambda function.

    'events' is a list of dictionaries, where the dict must contains the
    'schedule' of the event as string, and an optional 'name' and 'description'.

    :param awsclient:
    :param events: list of events
    :param lambda_name:
    :param alias_name:
    :return: exit_code
    """
    if not lambda_exists(awsclient, lambda_name):
        log.error(colored.red('The function you try to wire up doesn\'t ' +
                          'exist... Bailing out...'))
        return 1

    client_lambda = awsclient.get_client('lambda')
    lambda_function = client_lambda.get_function(FunctionName=lambda_name)
    lambda_arn = client_lambda.get_alias(FunctionName=lambda_name,
                                         Name=alias_name)['AliasArn']
    log.info('UN-wiring lambda_arn %s ' % lambda_arn)
    # TODO why load the policies here?
    '''
    policies = None
    try:
        result = client_lambda.get_policy(FunctionName=lambda_name,
                                          Qualifier=alias_name)
        policies = json.loads(result['Policy'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            log.warn("Permission policies not found")
        else:
            raise e
    '''

    if lambda_function is not None:
        #_unschedule_events(awsclient, events, lambda_arn)
        for event in events:
            evt_source = event['event_source']
            _remove_event_source(awsclient, evt_source, lambda_arn)
    return 0


################################################################################
### DEPRECATED
################################################################################
# all code and functionality below is deprectated (related to old wire implementation)
ENSURE_OPTIONS = ['absent', 'exists']


def wire_deprecated(awsclient, function_name, s3_event_sources=None,
                    time_event_sources=None,
                    alias_name=ALIAS_NAME):
    """Deprecated! Please use wire!


    :param awsclient:
    :param function_name:
    :param s3_event_sources: dictionary
    :param time_event_sources:
    :param alias_name:
    :return: exit_code
    """
    if not lambda_exists(awsclient, function_name):
        log.error(colored.red('The function you try to wire up doesn\'t ' +
                          'exist... Bailing out...'))
        return 1
    client_lambda = awsclient.get_client('lambda')
    lambda_function = client_lambda.get_function(FunctionName=function_name)
    lambda_arn = client_lambda.get_alias(FunctionName=function_name,
                                         Name=alias_name)['AliasArn']
    log.info('wiring lambda_arn %s ...' % lambda_arn)

    if lambda_function is not None:
        s3_events_ensure_exists, s3_events_ensure_absent = filter_events_ensure(
            s3_event_sources)
        cloudwatch_events_ensure_exists, cloudwatch_events_ensure_absent = \
            filter_events_ensure(time_event_sources)

        for s3_event_source in s3_events_ensure_absent:
            _ensure_s3_event(awsclient, s3_event_source, function_name,
                             alias_name, lambda_arn, s3_event_source['ensure'])
        for s3_event_source in s3_events_ensure_exists:
            _ensure_s3_event(awsclient, s3_event_source, function_name,
                             alias_name, lambda_arn, s3_event_source['ensure'])

        for time_event in cloudwatch_events_ensure_absent:
            _ensure_cloudwatch_event(awsclient, time_event, function_name,
                                     alias_name, lambda_arn,
                                     time_event['ensure'])
        for time_event in cloudwatch_events_ensure_exists:
            _ensure_cloudwatch_event(awsclient, time_event, function_name,
                                     alias_name, lambda_arn,
                                     time_event['ensure'])
    return 0


def unwire_deprecated(awsclient, function_name, s3_event_sources=None,
                      time_event_sources=None, alias_name=ALIAS_NAME):
    """Deprecated! Please use unwire!

    :param awsclient:
    :param function_name:
    :param s3_event_sources: dictionary
    :param time_event_sources:
    :param alias_name:
    :return: exit_code
    """
    if not lambda_exists(awsclient, function_name):
        log.error(colored.red('The function you try to wire up doesn\'t ' +
                          'exist... Bailing out...'))
        return 1

    client_lambda = awsclient.get_client('lambda')
    lambda_function = client_lambda.get_function(FunctionName=function_name)
    lambda_arn = client_lambda.get_alias(FunctionName=function_name,
                                         Name=alias_name)['AliasArn']
    log.info('UN-wiring lambda_arn %s ' % lambda_arn)
    policies = None
    try:
        result = client_lambda.get_policy(FunctionName=function_name,
                                          Qualifier=alias_name)
        policies = json.loads(result['Policy'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            log.warn("Permission policies not found")
        else:
            raise e

    if lambda_function is not None:
        #### S3 Events
        # for every permission - delete it and corresponding rule (if exists)
        if policies:
            for statement in policies['Statement']:
                if statement['Principal']['Service'] == 's3.amazonaws.com':
                    source_bucket = get_bucket_from_s3_arn(
                        statement['Condition']['ArnLike']['AWS:SourceArn'])
                    log.info('\tRemoving S3 permission {} invoking {}'.format(
                        source_bucket, lambda_arn))
                    _remove_permission(awsclient, function_name,
                                       statement['Sid'], alias_name)
                    log.info('\tRemoving All S3 events {} invoking {}'.format(
                        source_bucket, lambda_arn))
                    _remove_events_from_s3_bucket(awsclient, source_bucket,
                                                  lambda_arn)

        # Case: s3 events without permissions active "safety measure"
        for s3_event_source in s3_event_sources:
            bucket_name = s3_event_source.get('bucket')
            _remove_events_from_s3_bucket(awsclient, bucket_name, lambda_arn)

        #### CloudWatch Events
        # for every permission - delete it and corresponding rule (if exists)
        if policies:
            for statement in policies['Statement']:
                if statement['Principal']['Service'] == 'events.amazonaws.com':
                    rule_name = get_rule_name_from_event_arn(
                        statement['Condition']['ArnLike']['AWS:SourceArn'])
                    log.info(
                        '\tRemoving Cloudwatch permission {} invoking {}'.format(
                            rule_name, lambda_arn))
                    _remove_permission(awsclient, function_name,
                                       statement['Sid'], alias_name)
                    log.info('\tRemoving Cloudwatch rule {} invoking {}'.format(
                        rule_name, lambda_arn))
                    _remove_cloudwatch_rule_event(awsclient, rule_name,
                                                  lambda_arn)
        # Case: rules without permissions active, "safety measure"
        for time_event in time_event_sources:
            rule_name = time_event.get('ruleName')
            _remove_cloudwatch_rule_event(awsclient, rule_name, lambda_arn)

    return 0


def _remove_events_from_s3_bucket(awsclient, bucket_name, target_lambda_arn,
                                  filter_rule=False):
    if bucket_exists(awsclient, bucket_name):
        client_s3 = awsclient.get_client('s3')
        bucket_configurations = client_s3.get_bucket_notification_configuration(
            Bucket=bucket_name)
        bucket_configurations.pop('ResponseMetadata')
        matching_notifications, not_matching_notifications = \
            filter_bucket_notifications_with_arn(
                bucket_configurations.get('LambdaFunctionConfigurations', []),
                target_lambda_arn, filter_rule
            )
        if not_matching_notifications:
            bucket_configurations[
                'LambdaFunctionConfigurations'] = not_matching_notifications
        else:
            if 'LambdaFunctionConfigurations' in bucket_configurations:
                bucket_configurations.pop('LambdaFunctionConfigurations')

        response = client_s3.put_bucket_notification_configuration(
            Bucket=bucket_name,
            NotificationConfiguration=bucket_configurations
        )


def _remove_cloudwatch_rule_event(awsclient, rule_name, target_lambda_arn):
    client_event = awsclient.get_client('events')
    try:
        target_list = client_event.list_targets_by_rule(
            Rule=rule_name,
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return
        else:
            raise e
    target_id_list = []

    for target in target_list['Targets']:
        if target['Arn'] == target_lambda_arn:
            target_id_list += [target['Id']]
    # remove targets
    if target_id_list:
        client_event.remove_targets(
            Rule=rule_name,
            Ids=target_id_list,
        )
    # Delete rule only if all targets were associated with target_arn (i.e. only target target_arn function)
    if len(target_id_list) == len(target_list['Targets']) or (
                not target_id_list and not target_list):
        client_event.delete_rule(
            Name=rule_name
        )


def _ensure_cloudwatch_event(awsclient, time_event, function_name,
                             alias_name, lambda_arn, ensure='exists'):
    if not ensure in ENSURE_OPTIONS:
        log.error("{} is invalid ensure option, should be {}".format(ensure,
                                                                 ENSURE_OPTIONS))
        # TODO unbelievable: another sys.exit in library code!!!
        sys.exit(1)
    rule_name = time_event.get('ruleName')
    rule_description = time_event.get('ruleDescription')
    schedule_expression = time_event.get('scheduleExpression')
    client_event = awsclient.get_client('events')

    rule_exists = False
    schedule_expression_match = False
    not_matching_schedule_expression = None
    try:
        rule_response = client_event.describe_rule(Name=rule_name)
        rule_exists = True
        if rule_response['ScheduleExpression'] == schedule_expression:
            schedule_expression_match = True
        else:
            not_matching_schedule_expression = rule_response[
                'ScheduleExpression']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            pass
        else:
            raise e

    permission_exists = False
    if rule_exists:
        policies = _get_lambda_policies(awsclient, function_name, alias_name)
        if policies:
            for statement in policies['Statement']:
                if statement['Principal']['Service'] == 'events.amazonaws.com':
                    event_source_arn = get_rule_name_from_event_arn(
                        statement['Condition']['ArnLike']['AWS:SourceArn'])
                    if rule_name == event_source_arn:
                        permission_exists = statement['Sid']
                        break

    if not rule_exists and not permission_exists:
        if ensure == 'exists':
            log.info(colored.magenta(
                "\tWiring Cloudwatch event {}\n\t\t{}".format(rule_name,
                                                              schedule_expression)))
            rule_arn = _lambda_add_time_schedule_event_source(
                awsclient, rule_name, rule_description, schedule_expression,
                lambda_arn)
            _lambda_add_invoke_permission(
                awsclient, function_name, 'events.amazonaws.com', rule_arn)
        elif ensure == 'absent':
            return 0
    if rule_exists and permission_exists:
        if ensure == 'exists':
            if schedule_expression_match:
                return 0
            else:
                log.info(colored.magenta(
                    "\t Updating Cloudwatch event {}\n\t\tOld: {}\n\t\tTo: {}".format(
                        rule_name,
                        not_matching_schedule_expression,
                        schedule_expression)))
                rule_arn = _lambda_add_time_schedule_event_source(
                    awsclient, rule_name, rule_description,
                    schedule_expression, lambda_arn)
        if ensure == 'absent':
            log.info(colored.magenta("\tRemoving rule {}\n\t\t{}".format(rule_name,
                                                                      schedule_expression)))
            _remove_permission(awsclient, function_name, statement['Sid'],
                               alias_name)
            _remove_cloudwatch_rule_event(awsclient, rule_name, lambda_arn)


def _wire_s3_to_lambda(awsclient, s3_event_source, function_name,
                       target_lambda_arn):
    bucket_name = s3_event_source.get('bucket')
    event_type = s3_event_source.get('type')
    prefix = s3_event_source.get('prefix', None)
    suffix = s3_event_source.get('suffix', None)
    s3_arn = create_aws_s3_arn(bucket_name)

    _lambda_add_invoke_permission(awsclient, function_name,
                                  's3.amazonaws.com', s3_arn)
    _lambda_add_s3_event_source(awsclient, target_lambda_arn, event_type,
                                bucket_name, prefix, suffix)


def filter_events_ensure(evt_sources):
    events_ensure_exists = []
    events_ensure_absent = []
    for event in evt_sources:
        if 'ensure' in event:
            if event['ensure'] == 'exists':
                events_ensure_exists.append(event)
            elif event['ensure'] == 'absent':
                events_ensure_absent.append(event)
            else:
                log.error(colored.red(
                    'Ensure must be one of {}, currently set to {}'.format(
                        ENSURE_OPTIONS, event['ensure'])))
                # FIXME exit in lib code!
                # TODO: make sure it has a test!
                # TODO unbelievable: another sys.exit in library code!!!
                sys.exit(1)
        else:
            event['ensure'] = 'exists'
            events_ensure_exists.append(event)
    return events_ensure_exists, events_ensure_absent


def _ensure_s3_event(awsclient, s3_event_source, function_name, alias_name,
                     target_lambda_arn, ensure="exists"):
    if ensure not in ENSURE_OPTIONS:
        log.info("{} is invalid ensure option, should be {}".format(ensure,
                                                                 ENSURE_OPTIONS))

    client_s3 = awsclient.get_client('s3')

    bucket_name = s3_event_source.get('bucket')
    event_type = s3_event_source.get('type')
    prefix = s3_event_source.get('prefix', None)
    suffix = s3_event_source.get('suffix', None)

    rule_exists = False
    filter_rules = build_filter_rules(prefix, suffix)

    bucket_configurations = client_s3.get_bucket_notification_configuration(
        Bucket=bucket_name)
    bucket_configurations.pop('ResponseMetadata')
    matching_notifications, not_matching_notifications = filter_bucket_notifications_with_arn(
        bucket_configurations.get('LambdaFunctionConfigurations', []),
        target_lambda_arn, filter_rules)

    for config in matching_notifications:
        if config['Events'][0] == event_type:
            if filter_rules:
                if list_of_dict_equals(filter_rules,
                                       config['Filter']['Key']['FilterRules']):
                    rule_exists = True
            else:
                rule_exists = True
    # permissions_exists
    permission_exists = False
    if rule_exists:
        policies = _get_lambda_policies(awsclient, function_name, alias_name)
        if policies:
            for statement in policies['Statement']:
                if statement['Principal']['Service'] == 's3.amazonaws.com':
                    permission_bucket = get_bucket_from_s3_arn(
                        statement['Condition']['ArnLike']['AWS:SourceArn'])
                    if permission_bucket == bucket_name:
                        permission_exists = statement['Sid']
                        break

    if not rule_exists and not permission_exists:
        if ensure == "exists":
            log.info(colored.magenta(
                "\tWiring rule {}: {}".format(bucket_name, event_type)))
            for rule in filter_rules:
                log.info(colored.magenta(
                    '\t\t{}: {}'.format(rule['Name'], rule['Value'])))
            _wire_s3_to_lambda(awsclient, s3_event_source, function_name,
                               target_lambda_arn)
        elif ensure == "absent":
            return 0
    if rule_exists and permission_exists:
        if ensure == "absent":
            log.info(colored.magenta(
                "\tRemoving rule {}: {}".format(bucket_name, event_type)))
            for rule in filter_rules:
                log.info(colored.magenta(
                    '\t\t{}: {}'.format(rule['Name'], rule['Value'])))
            _remove_permission(awsclient, function_name, permission_exists,
                               alias_name)
            _remove_events_from_s3_bucket(awsclient, bucket_name,
                                          target_lambda_arn,
                                          filter_rules)


def _lambda_add_time_schedule_event_source(awsclient, rule_name,
                                           rule_description,
                                           schedule_expression, lambda_arn):
    client_event = awsclient.get_client('events')
    client_event.put_rule(
        Name=rule_name,
        ScheduleExpression=schedule_expression,
        Description=rule_description,
    )
    rule_response = client_event.describe_rule(Name=rule_name)
    if rule_response is not None:
        client_event.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': lambda_arn,
                },
            ]
        )

    return rule_response['Arn']


def _get_lambda_policies(awsclient, function_name, alias_name):
    client_lambda = awsclient.get_client('lambda')
    policies = None
    try:
        result = client_lambda.get_policy(FunctionName=function_name,
                                          Qualifier=alias_name)
        policies = json.loads(result['Policy'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            log.info(colored.red("Permission policies not found"))
        else:
            raise e
    return policies


def _remove_permission(awsclient, function_name, statement_id, qualifier):
    client_lambda = awsclient.get_client('lambda')
    response_remove = client_lambda.remove_permission(
        FunctionName=function_name,
        StatementId=statement_id,
        Qualifier=qualifier
    )


def _lambda_add_invoke_permission(awsclient, function_name,
                                  source_principal,
                                  source_arn, alias_name=ALIAS_NAME):
    # https://www.getoto.net/noise/2015/08/20/better-together-amazon-ecs-and-aws-lambda/
    # http://docs.aws.amazon.com/cli/latest/reference/lambda/add-permission.html
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.add_permission(
        FunctionName=function_name,
        StatementId=str(uuid.uuid1()),
        Action='lambda:InvokeFunction',
        Principal=source_principal,
        SourceArn=source_arn,
        Qualifier=alias_name
    )
    return response


def _lambda_add_s3_event_source(awsclient, arn, event, bucket, prefix,
                                suffix):
    """Use only prefix OR suffix

    :param arn:
    :param event:
    :param bucket:
    :param prefix:
    :param suffix:
    :return:
    """
    json_data = {
        'LambdaFunctionConfigurations': [{
            'LambdaFunctionArn': arn,
            'Id': str(uuid.uuid1()),
            'Events': [event]
        }]
    }

    filter_rules = build_filter_rules(prefix, suffix)

    json_data['LambdaFunctionConfigurations'][0].update({
        'Filter': {
            'Key': {
                'FilterRules': filter_rules
            }
        }
    })
    # http://docs.aws.amazon.com/cli/latest/reference/s3api/put-bucket-notification-configuration.html
    # http://docs.aws.amazon.com/AmazonS3/latest/dev/NotificationHowTo.html
    client_s3 = awsclient.get_client('s3')

    bucket_configurations = client_s3.get_bucket_notification_configuration(
        Bucket=bucket)
    bucket_configurations.pop('ResponseMetadata')

    if 'LambdaFunctionConfigurations' in bucket_configurations:
        bucket_configurations['LambdaFunctionConfigurations'].append(
            json_data['LambdaFunctionConfigurations'][0]
        )
    else:
        bucket_configurations['LambdaFunctionConfigurations'] = json_data[
            'LambdaFunctionConfigurations']

    response = client_s3.put_bucket_notification_configuration(
        Bucket=bucket,
        NotificationConfiguration=bucket_configurations
    )
    # TODO don't return a table, but success state
    return json2table(response)
