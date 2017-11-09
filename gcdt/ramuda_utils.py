# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import base64
import hashlib
import logging
import sys
import threading
import time

import maya
import os
from s3transfer import S3Transfer

from gcdt.utils import GracefulExit
from . import utils

PY3 = sys.version_info[0] >= 3

if PY3:
    unicode = str


log = logging.getLogger(__name__)


def lambda_exists(awsclient, lambda_name):
    client_lambda = awsclient.get_client('lambda')
    try:
        client_lambda.get_function(FunctionName=lambda_name)
    except GracefulExit:
        raise
    except Exception as e:
        return False
    else:
        return True


def unit(name):
    # used in get_metrics
    if name == 'Duration':
        return 'Milliseconds'
    else:
        return 'Count'


def aggregate_datapoints(datapoints):
    # used in ramuda_core.get_metrics
    # this does not round, it truncates!
    result = 0.0
    for dp in datapoints:
        result += dp['Sum']
    return int(result)


def list_lambda_versions(awsclient, function_name):  # this is not used!!
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.list_versions_by_function(
        FunctionName=function_name,
    )
    log.debug(response)
    return response


def create_sha256(code):
    if isinstance(code, unicode):
        code = code.encode('utf-8')
    return base64.b64encode(hashlib.sha256(code).digest())


def create_sha256_urlsafe(code):
    if isinstance(code, unicode):
        code = code.encode('utf-8')
    return base64.urlsafe_b64encode(hashlib.sha256(code).digest())


def create_aws_s3_arn(bucket_name):
    return 'arn:aws:s3:::' + bucket_name


def get_bucket_from_s3_arn(aws_s3_arn):
    # "arn:aws:s3:::test-bucket-dp-723" mirrors _create_aws_s3_arn
    return aws_s3_arn.split(':')[5]


def get_rule_name_from_event_arn(aws_event_arn):
    # ex. 'arn:aws:events:eu-west-1:111537987451:rule/dp-preprod-test-dp-723-T1_fun2'
    full_rule = aws_event_arn.split(':')[5]
    return full_rule.split('/')[1]


def get_remote_code_hash(awsclient, function_name):
    client_lambda = awsclient.get_client('lambda')
    response = client_lambda.get_function_configuration(
        FunctionName=function_name)
    return response['CodeSha256']


def list_of_dict_equals(dict1, dict2):
    if len(dict1) == len(dict2):
        for d in dict1:
            if d not in dict2:
                return False
    else:
        return False
    return True


def build_filter_rules(prefix, suffix):
    filter_rules = []
    if prefix:
        filter_rules.append(
            {
                'Name': 'Prefix',
                'Value': prefix
            }
        )
    if suffix:
        filter_rules.append(
            {
                'Name': 'Suffix',
                'Value': suffix
            }
        )
    return filter_rules


class ProgressPercentage(object):
    def __init__(self, filename, out=sys.stdout):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._time = time.time()
        self._time_max = 360
        self._out = out

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        # FIXME: ZeroDivisionError: float division by zero
        # in case of empty file (_size == 0)
        with self._lock:
            self._seen_so_far += bytes_amount

            percentage = (self._seen_so_far / self._size) * 100
            elapsed_time = (time.time() - self._time)
            time_left = self._time_max - elapsed_time
            bytes_per_second = self._seen_so_far / elapsed_time
            if (self._size / bytes_per_second > time_left) and time_left < 330:
                log.warn('bad connection')
                raise Exception
            self._out.write(' elapsed time %ds, time left %ds, bps %d' %
                            (int(elapsed_time), int(time_left),
                             int(bytes_per_second)))
            self._out.flush()
            self._out.write(
                '\r%s  %s / %s  (%.2f%%)' % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            self._out.flush()


# TODO move this to s3 module
@utils.retries(3)
def s3_upload(awsclient, deploy_bucket, zipfile, lambda_name):
    client_s3 = awsclient.get_client('s3')
    region = client_s3.meta.region_name
    transfer = S3Transfer(client_s3)
    bucket = deploy_bucket

    if not zipfile:
        return
    local_hash = str(create_sha256_urlsafe(zipfile))

    # ramuda/eu-west-1/<lambda_name>/<local_hash>.zip
    dest_key = 'ramuda/%s/%s/%s.zip' % (region, lambda_name, local_hash)

    source_filename = '/tmp/' + local_hash
    with open(source_filename, 'wb') as source_file:
        source_file.write(zipfile)

    # print 'uploading to S3'
    # start = time.time()
    transfer.upload_file(source_filename, bucket, dest_key,
                         callback=ProgressPercentage(source_filename))
    # end = time.time()
    # print 'uploading took:'
    # print(end - start)

    response = client_s3.head_object(Bucket=bucket, Key=dest_key)
    # print '\n'
    # print response['ETag']
    # print response['VersionId']
    # print(dest_key)
    # print()
    return dest_key, response['ETag'], response['VersionId']


# helpers for ramuda logs command
def check_and_format_logs_params(start, end, tail):
    """Helper to read the params for the logs command"""
    def _decode_duration_type(duration_type):
        durations = {'m': 'minutes', 'h': 'hours', 'd': 'days', 'w': 'weeks'}
        return durations[duration_type]

    if not start:
        if tail:
            start_dt = maya.now().subtract(seconds=300).datetime(naive=True)
        else:
            start_dt = maya.now().subtract(days=1).datetime(naive=True)
    elif start and start[-1] in ['m', 'h', 'd', 'w']:
        value = int(start[:-1])
        start_dt = maya.now().subtract(
            **{_decode_duration_type(start[-1]): value}).datetime(naive=True)
    elif start:
        start_dt = maya.parse(start).datetime(naive=True)

    if end and end[-1] in ['m', 'h', 'd', 'w']:
        value = int(end[:-1])
        end_dt = maya.now().subtract(
            **{_decode_duration_type(end[-1]): value}).datetime(naive=True)
    elif end:
        end_dt = maya.parse(end).datetime(naive=True)
    else:
        end_dt = None
    return start_dt, end_dt


def filter_bucket_notifications_with_arn(lambda_function_configurations,
                                         lambda_arn, filter_rules=False):
    matching_notifications = []
    not_matching_notifications = []
    for notification in lambda_function_configurations:
        if notification["LambdaFunctionArn"] == lambda_arn:
            if filter_rules:
                existing_filter = notification['Filter']['Key']['FilterRules']
                if list_of_dict_equals(filter_rules, existing_filter):
                    matching_notifications.append(notification)
                else:
                    not_matching_notifications.append(notification)
            else:
                matching_notifications.append(notification)
        else:
            not_matching_notifications.append(notification)
    return matching_notifications, not_matching_notifications


def all_pages(method, request, accessor, cond=None):
    """Helper to process all pages using botocore service methods (exhausts NextToken).
    note: `cond` is optional... you can use it to make filtering more explicit
    if you like. Alternatively you can do the filtering in the `accessor` which
    is perfectly fine, too
    Note: there is a generic helper for this in utils but lambda uses a slightly
    different mechanism so we need this here.

    :param method: service method
    :param request: request dictionary for service call
    :param accessor: function to extract data from each response
    :param cond: filter function to return True / False based on a response
    :return: list of collected resources
    """
    if cond is None:
        cond = lambda x: True
    result = []
    next_token = None
    while True:
        if next_token:
            request['Marker'] = next_token
        response = method(**request)
        if cond(response):
            data = accessor(response)
            if data:
                if isinstance(data, list):
                    result.extend(data)
                else:
                    result.append(data)
        if 'NextMarker' not in response:
            break
        next_token = response['NextMarker']

    return result
