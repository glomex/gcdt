# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import base64
import datetime
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
                print('bad connection')
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
    print()
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


def decode_format_timestamp(timestamp):
    """Convert unix timestamp (millis) into date & time we use in logs output.

    :param timestamp: unix timestamp in millis
    :return: date, time in UTC
    """
    dt = maya.MayaDT(timestamp/1000).datetime(naive=True)
    return dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M:%S')


def datetime_to_timestamp(dt):
    """Convert datetime to millis since epoc.

    :param dt:
    :return: milliseconds since 1970-01-01
    """
    #return int((dt - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)
    return int(maya.MayaDT.from_datetime(dt)._epoch * 1000)
