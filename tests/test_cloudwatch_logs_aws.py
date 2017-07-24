# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import time

import pytest
import maya
from gcdt.cloudwatch_logs import delete_log_group, put_retention_policy, \
    describe_log_group, create_log_stream, put_log_events, create_log_group, \
    filter_log_events, describe_log_stream, get_log_events, check_log_stream_exists

from gcdt.cloudwatch_logs import decode_format_timestamp, datetime_to_timestamp

from gcdt_testtools import helpers
from gcdt_testtools.helpers_aws import awsclient  # fixture!
from gcdt_testtools.helpers_aws import check_preconditions


@pytest.mark.aws
@check_preconditions
def test_log_group_lifecycle(awsclient):
    # Note: with this we do not want to test AWS cloudwatch
    # we only want to make sure our wrappers for AWS calls work
    # easiest to achieve this is to test a whole log group lifecycle
    fake_log_group_name = '/aws/lambda/unittest_loggroup_%s' % helpers.random_string()
    fake_log_stream_name = 'unittest_logstream_%s' % helpers.random_string()

    create_log_group(awsclient, fake_log_group_name)
    create_log_stream(awsclient, fake_log_group_name, fake_log_stream_name)

    stream_info = describe_log_stream(awsclient, fake_log_group_name, fake_log_stream_name)
    assert stream_info['arn'].endswith(
        ':log-group:%s:log-stream:%s' % (fake_log_group_name, fake_log_stream_name))
    assert 'creationTime' in stream_info
    assert stream_info['logStreamName'] == fake_log_stream_name
    assert stream_info['storedBytes'] == 0

    put_retention_policy(awsclient, fake_log_group_name, 545)
    grp_info = describe_log_group(awsclient, fake_log_group_name)
    assert grp_info['retentionInDays'] == 545
    assert grp_info['storedBytes'] == 0

    my_log_event = {
        'timestamp': int(time.time()) * 1000,  # time in millis!!
        'message': 'meine oma fährt im hühnerstall motorrad'
    }
    put_log_events(awsclient, fake_log_group_name, fake_log_stream_name,
                   [my_log_event])

    delete_log_group(awsclient, fake_log_group_name)
    # now we should not store anything anymore
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info is None


@pytest.mark.aws
@check_preconditions
def test_set_retention_on_not_yet_existing_log_group(awsclient):
    fake_log_group_name = '/aws/lambda/%s' % helpers.random_string()

    put_retention_policy(awsclient, fake_log_group_name, 545)
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info['retentionInDays'] == 545
    assert info['storedBytes'] == 0

    delete_log_group(awsclient, fake_log_group_name)
    # now we should not store anything anymore
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info is None


@pytest.mark.aws
@check_preconditions
def test_filter_log_events(awsclient):
    fake_log_group_name = '/aws/lambda/unittest_loggroup_%s' % helpers.random_string()
    fake_log_stream_name = 'unittest_logstream_%s' % helpers.random_string()

    create_log_group(awsclient, fake_log_group_name)
    create_log_stream(awsclient, fake_log_group_name, fake_log_stream_name)

    put_retention_policy(awsclient, fake_log_group_name, 545)

    info = describe_log_group(awsclient, fake_log_group_name)
    assert info['retentionInDays'] == 545
    assert info['storedBytes'] == 0

    now = helpers.time_now()
    log_event1 = {
        'timestamp': now - 300000,  # 5min
        'message': '1_meine oma fährt im hühnerstall motorrad'
    }
    log_event2 = {
        'timestamp': now - 120000,  # 2 min
        'message': '2_meine oma fährt im hühnerstall motorrad'
    }
    log_event3 = {
        'timestamp': now - 10000,   # 10 sec
        'message': '3_meine oma fährt im hühnerstall motorrad'
    }
    put_log_events(awsclient, fake_log_group_name, fake_log_stream_name,
                   [log_event1, log_event2, log_event3])

    # this testcase is potentially flaky since we depend on the log events
    # to eventually arrive in AWS cloudwatch
    time.sleep(10)  # automatically removed in playback mode!

    # filter log events
    logentries = filter_log_events(awsclient, fake_log_group_name,
                                   now - 180000, now - 60000)
    assert logentries == [log_event2]

    delete_log_group(awsclient, fake_log_group_name)
    # now we should not store anything anymore
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info is None


def test_decode_format_timestamp():
    timestamp = 1499353246961  # in millis
    exp_date = '2017-07-06'
    exp_time = '15:00:46'
    assert decode_format_timestamp(timestamp) == (exp_date, exp_time)


def test_datetime_to_timestamp():
    exp_timestamp = 1499353246961  # in millis
    dt = maya.when('2017-07-06 15:00:46.961').datetime(naive=True)
    assert datetime_to_timestamp(dt) == exp_timestamp


@pytest.mark.aws
@check_preconditions
def test_get_log_events(awsclient):
    fake_log_group_name = '/aws/lambda/unittest_loggroup_%s' % helpers.random_string()
    fake_log_stream_name = 'unittest_logstream_%s' % helpers.random_string()

    create_log_group(awsclient, fake_log_group_name)
    create_log_stream(awsclient, fake_log_group_name, fake_log_stream_name)

    put_retention_policy(awsclient, fake_log_group_name, 545)

    info = describe_log_group(awsclient, fake_log_group_name)
    assert info['retentionInDays'] == 545
    assert info['storedBytes'] == 0

    now = helpers.time_now()
    log_event1 = {
        'timestamp': now - 300000,  # 5min
        'message': '1_meine oma fährt im hühnerstall motorrad'
    }
    log_event2 = {
        'timestamp': now - 120000,  # 2 min
        'message': '2_meine oma fährt im hühnerstall motorrad'
    }
    log_event3 = {
        'timestamp': now - 10000,   # 10 sec
        'message': '3_meine oma fährt im hühnerstall motorrad'
    }
    put_log_events(awsclient, fake_log_group_name, fake_log_stream_name,
                   [log_event1, log_event2, log_event3])

    # this testcase is potentially flaky since we depend on the log events
    # to eventually arrive in AWS cloudwatch
    time.sleep(10)  # automatically removed in playback mode!

    # get log events
    logentries = get_log_events(awsclient, fake_log_group_name,
                                fake_log_stream_name, now - 180000)
    assert logentries == [log_event2, log_event3]

    delete_log_group(awsclient, fake_log_group_name)
    # now we should not store anything anymore
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info is None


@pytest.mark.aws
@check_preconditions
def test_check_log_stream_exists_no_stream(awsclient):
    fake_log_group_name = '/aws/lambda/unittest_loggroup_%s' % helpers.random_string()
    fake_log_stream_name = 'unittest_logstream_%s' % helpers.random_string()

    create_log_group(awsclient, fake_log_group_name)
    assert not check_log_stream_exists(awsclient, fake_log_group_name, fake_log_stream_name)

    # clean up
    delete_log_group(awsclient, fake_log_group_name)


@pytest.mark.aws
@check_preconditions
def test_check_log_stream_exists_no_log_group(awsclient):
    fake_log_group_name = '/aws/lambda/unittest_loggroup_%s' % helpers.random_string()
    fake_log_stream_name = 'unittest_logstream_%s' % helpers.random_string()
    assert not check_log_stream_exists(awsclient, fake_log_group_name, fake_log_stream_name)
    # clean up


@pytest.mark.aws
@check_preconditions
def test_check_log_stream_exists(awsclient):
    fake_log_group_name = '/aws/lambda/unittest_loggroup_%s' % helpers.random_string()
    fake_log_stream_name = 'unittest_logstream_%s' % helpers.random_string()

    create_log_group(awsclient, fake_log_group_name)
    create_log_stream(awsclient, fake_log_group_name, fake_log_stream_name)
    assert check_log_stream_exists(awsclient, fake_log_group_name, fake_log_stream_name)

    # clean up
    delete_log_group(awsclient, fake_log_group_name)


