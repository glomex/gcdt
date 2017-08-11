# -*- coding: utf-8 -*-

"""A bunch of helper functions to manage cloudwatch logs
botocore docs: http://botocore.readthedocs.io/en/latest/reference/services/logs.html
"""

from __future__ import unicode_literals, print_function

import maya
from .gcdt_logging import getLogger

from .utils import GracefulExit


log = getLogger(__name__)


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
    # TODO use all_pages instead!
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
        return


def describe_log_stream(awsclient, log_group_name, log_stream_name):
    """Get info on the specified log stream

    :param log_group_name: log group name
    :param log_stream_name: log stream
    :return:
    """
    client_logs = awsclient.get_client('logs')

    response = client_logs.describe_log_streams(
        logGroupName=log_group_name,
        logStreamNamePrefix=log_stream_name,
        limit=1
    )
    if response['logStreams']:
        return response['logStreams'][0]
    else:
        return


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
        log.warn(response['rejectedLogEventsInfo'])
    if 'nextSequenceToken' in response:
        return response['nextSequenceToken']


def get_log_events(awsclient, log_group_name, log_stream_name, start_ts=None):
    """Get log events for the specified log group and stream.
    this is used in tenkai output instance diagnostics

    :param log_group_name: log group name
    :param log_stream_name: log stream name
    :param start_ts: timestamp
    :return:
    """
    client_logs = awsclient.get_client('logs')

    request = {
        'logGroupName': log_group_name,
        'logStreamName': log_stream_name
    }
    if start_ts:
        request['startTime'] = start_ts

    # TODO exhaust the events!
    # TODO use all_pages !
    response = client_logs.get_log_events(**request)

    if 'events' in response and response['events']:
        return [{'timestamp': e['timestamp'], 'message': e['message']}
                for e in response['events']]


def check_log_stream_exists(awsclient, log_group_name, log_stream_name):
    """Check

    :param log_group_name: log group name
    :param log_stream_name: log stream name
    :return: True / False
    """
    lg = describe_log_group(awsclient, log_group_name)
    if lg and lg['logGroupName'] == log_group_name:
        stream = describe_log_stream(awsclient, log_group_name, log_stream_name)
        if stream and stream['logStreamName'] == log_stream_name:
            return True
    return False


def decode_format_timestamp(timestamp):
    """Convert unix timestamp (millis) into date & time we use in logs output.

    :param timestamp: unix timestamp in millis
    :return: date, time in UTC
    """
    dt = maya.MayaDT(timestamp / 1000).datetime(naive=True)
    return dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M:%S')


def datetime_to_timestamp(dt):
    """Convert datetime to millis since epoc.

    :param dt:
    :return: milliseconds since 1970-01-01
    """
    # return int((dt - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)
    return int(maya.MayaDT.from_datetime(dt)._epoch * 1000)
