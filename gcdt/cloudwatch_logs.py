# -*- coding: utf-8 -*-

"""A bunch of helper functions to manage cloudwatch logs
botocore docs: http://botocore.readthedocs.io/en/latest/reference/services/logs.html
"""

from __future__ import unicode_literals, print_function

from .utils import GracefulExit


def delete_log_group(awsclient, log_group_name):
    """Delete the specified log group
    
    :param log_group_name: log group name
    :return: 
    """
    client_logs = awsclient.get_client('logs')

    response = client_logs.delete_log_group(
        logGroupName=log_group_name
    )


def put_retention_policy(awsclient, log_group_name, retention_in_days):
    """Sets the retention of the specified log group
    if the log group does not yet exist than it will be created first.

    :param log_group_name: log group name
    :param retention_in_days: log group name
    :return:
    """
    try:
        # Note: for AWS Lambda the log_group is created once the first
        # log event occurs. So if the log_group does not exist we create it
        create_log_group(awsclient, log_group_name)
    except GracefulExit:
        raise
    except Exception:
        # TODO check that it is really a ResourceAlreadyExistsException
        pass

    client_logs = awsclient.get_client('logs')
    response = client_logs.put_retention_policy(
        logGroupName=log_group_name,
        retentionInDays=retention_in_days
    )


def filter_log_events(awsclient, log_group_name, start_ts, end_ts=None):
    """
    Note: this is used to retrieve logs in ramuda.

    :param log_group_name: log group name
    :param start_ts: timestamp
    :param end_ts: timestamp
    :return: list of log entries
    """
    client_logs = awsclient.get_client('logs')
    logs = []
    next_token = None
    while True:
        request = {
            'logGroupName': log_group_name,
            'startTime': start_ts
        }
        if end_ts:
            request['endTime'] = end_ts
        if next_token:
            request['nextToken'] = next_token
        response = client_logs.filter_log_events(**request)
        logs.extend(
            [{'timestamp': e['timestamp'], 'message': e['message']}
             for e in response['events']]
        )
        if 'nextToken' not in response:
            break
        next_token = response['nextToken']
    return logs


# these functions we need so we can test a log group lifecycle
def describe_log_group(awsclient, log_group_name):
    """Get info on the specified log group

    :param log_group_name: log group name
    :return:
    """
    client_logs = awsclient.get_client('logs')

    request = {
        'logGroupNamePrefix': log_group_name,
        'limit': 1
    }
    response = client_logs.describe_log_groups(**request)
    if response['logGroups']:
        return response['logGroups'][0]
    else:
        return {}


def describe_log_stream(awsclient, log_group_name, log_stream_name):
    """Get info on the specified log stream

    :param log_group_name: log group name
    :param log_stream_name: log stream
    :return:
    """
    client_logs = awsclient.get_client('logs')

    response = client_logs.describe_log_groups(
        logGroupNamePrefix=log_group_name,
        limit=1
    )
    if response['logGroups']:
        return response['logGroups'][0]
    else:
        return {}


'''
# currently no waiters implemented for cloudwatch logs
def wait_for_logs(awsclient):
    client_logs = awsclient.get_client('logs')
    #waiter = client_logs.get_waiter('stack_completed')
    #waiter.wait(StackName='Blah')
    waiter = client_logs.get_waiter('stack_completed')
    waiter.wait(StackName='Blah')
'''


def create_log_group(awsclient, log_group_name):
    """Creates a log group with the specified name.

    :param log_group_name: log group name
    :return:
    """
    client_logs = awsclient.get_client('logs')

    response = client_logs.create_log_group(
        logGroupName=log_group_name,
    )


def create_log_stream(awsclient, log_group_name, log_stream_name):
    """Creates a log stream for the specified log group.

    :param log_group_name: log group name
    :param log_stream_name: log stream name
    :return:
    """
    client_logs = awsclient.get_client('logs')

    response = client_logs.create_log_stream(
        logGroupName=log_group_name,
        logStreamName=log_stream_name
    )


def put_log_events(awsclient, log_group_name, log_stream_name, log_events,
                   sequence_token=None):
    """Put log events for the specified log group and stream.

    :param log_group_name: log group name
    :param log_stream_name: log stream name
    :param log_events: [{'timestamp': 123, 'message': 'string'}, ...]
    :param sequence_token: the sequence token
    :return: next_token
    """
    client_logs = awsclient.get_client('logs')
    request = {
        'logGroupName': log_group_name,
        'logStreamName': log_stream_name,
        'logEvents': log_events
    }
    if sequence_token:
        request['sequenceToken'] = sequence_token

    response = client_logs.put_log_events(**request)
    if 'rejectedLogEventsInfo' in response:
        print(response['rejectedLogEventsInfo'])
    if 'nextSequenceToken' in response:
        return response['nextSequenceToken']


'''
def get_log_events(awsclient, log_group_name, log_stream_name):
    """Get log events for the specified log group and stream.

    :param log_group_name: log group name
    :param log_stream_name: log stream name
    :return:
    """
    client_logs = awsclient.get_client('logs')

    response = client_logs.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
    )

    if 'events' in response and response['events']:
        return response['events']
'''
