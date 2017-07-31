# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys
import logging
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from tempfile import NamedTemporaryFile
import time

from s3transfer.subscribers import BaseSubscriber
from nose.tools import assert_regexp_matches
import pytest
import mock
import maya

from gcdt.ramuda_core import cleanup_bundle, bundle_lambda
from gcdt.ramuda_utils import unit, \
    aggregate_datapoints, create_sha256, ProgressPercentage, \
    list_of_dict_equals, create_aws_s3_arn, get_rule_name_from_event_arn, \
    get_bucket_from_s3_arn, build_filter_rules, create_sha256_urlsafe, \
    check_and_format_logs_params
from gcdt.utils import json2table
from gcdt_testtools.helpers import create_tempfile, get_size, temp_folder, \
    cleanup_tempfiles
from gcdt_testtools.helpers import logcapture  # fixtures!
from . import here


PY3 = sys.version_info[0] >= 3
log = logging.getLogger(__name__)


def test_cleanup_bundle(temp_folder):
    os.environ['ENV'] = 'DEV'
    paths_to_clean = ['vendored', 'bundle.zip']
    for path in paths_to_clean:
        if path.find('.') != -1:
            open(path, 'a').close()
        else:
            os.mkdir(path)
    cleanup_bundle()
    for path in paths_to_clean:
        assert not os.path.exists(path)


def test_unit():
    assert unit('Duration') == 'Milliseconds'
    assert unit('Else') == 'Count'


def test_aggregate_datapoints():
    assert aggregate_datapoints(
        [{'Sum': 0.1}, {'Sum': 0.1}, {'Sum': 0.1}, {'Sum': 0.1}, {'Sum': 0.1},
         {'Sum': 0.1}]) == 0
    assert aggregate_datapoints(
        [{'Sum': 1.1}, {'Sum': 1.1}, {'Sum': 1.1}, {'Sum': 1.1}]) == 4


def test_create_sha256():
    actual = create_sha256('Meine Oma fährt im Hühnerstall Motorrad')
    expected = b'SM6siXnsKAmQuG5egM0MYKgUU60nLFxUVeEvTcN4OFI='
    assert actual == expected


def test_create_sha256_urlsafe():
    actual = create_sha256_urlsafe('Meine Oma fährt im Hühnerstall Motorrad')
    expected = b'SM6siXnsKAmQuG5egM0MYKgUU60nLFxUVeEvTcN4OFI='
    assert actual == expected


def test_create_sha256_urlsafe_2():
    code = r'PK\x03\x04\x14\x00\x00\x00\x08\x00zg+JQ\xbbI\xd6\xba\x8e\x00\x00\x8dx\x02\x00\x0c\x00\x00\x00pyparsing.py\xec\xbd\xfb...\xa4\x81%\xdd\x01\x00handler_no_ping.pyPK\x05\x06\x00\x00\x00\x00\x1f\x00\x1f\x00\xcf\x08\x00\x00Y\xde\x01\x00\x00\x00'
    actual = create_sha256_urlsafe(code)
    expected = b'MH2eL07LPCviHtWFuiKxBgonjp3NEY-xzrIXBBssPiQ='
    assert actual == expected


def test_create_s3_arn():
    s3_arn = create_aws_s3_arn('dp-dev-not-existing')
    assert s3_arn == 'arn:aws:s3:::dp-dev-not-existing'


def test_get_bucket_name_from_s3_arn():
    s3_arn = 'arn:aws:s3:::test-bucket-dp-723'
    bucket_name = get_bucket_from_s3_arn(s3_arn)
    assert bucket_name == 'test-bucket-dp-723'


def test_get_rule_name_from_event_arn():
    rule_arn = 'arn:aws:events:eu-west-1:111537987451:rule/dp-preprod-test-dp-723-T1_fun2'
    rule_name = get_rule_name_from_event_arn(rule_arn)
    assert rule_name == 'dp-preprod-test-dp-723-T1_fun2'


def test_list_of_dicts():
    list_1 = [
        {"key1" : "value1"},
        {"key2" : "value2"},
        {"key3" : "value3"},
    ]
    list_2 = [
        {"key1" : "value1"},
        {"key2" : "value2"},
        {"key3" : "value3"},
    ]
    list_3 = [
        {"key1" : "value1"},
        {"key2" : "value2"},
    ]
    assert list_of_dict_equals(list_1, list_2) is True
    assert list_of_dict_equals(list_1, list_3) is False


def test_build_filter_rules():
    prefix = 'folder'
    suffix = '.gz'
    rules = build_filter_rules(prefix, suffix)

    rules_hardcoded = [
        { 'Name': 'Prefix',
          'Value': 'folder'},
        {'Name': 'Suffix',
         'Value': '.gz'}
    ]
    match = list_of_dict_equals(rules, rules_hardcoded)
    assert match is True


def test_progress_percentage(cleanup_tempfiles):
    class ProgressCallbackInvoker(BaseSubscriber):
        """A back-compat wrapper to invoke a provided callback via a subscriber

        :param callback: A callable that takes a single positional argument for
            how many bytes were transferred.
        """
        def __init__(self, callback):
            self._callback = callback

        def on_progress(self, bytes_transferred, **kwargs):
            self._callback(bytes_transferred)

    # create dummy file
    tf = NamedTemporaryFile(delete=False, suffix='.tgz')
    cleanup_tempfiles.append(tf.name)
    open(tf.name, 'w').write('some content here...')
    out = StringIO()
    # instantiate ProgressReporter
    callback = ProgressPercentage(tf.name, out=out)
    subscriber = ProgressCallbackInvoker(callback)
    # 1 byte -> 5%
    time.sleep(0.001)
    subscriber.on_progress(bytes_transferred=1)
    assert_regexp_matches(out.getvalue().strip(),
                          '.*\.tgz  1 / 20\.0  \(5\.00%\)')
    # 11 (1+10) byte -> 55%
    subscriber.on_progress(bytes_transferred=10)
    assert_regexp_matches(out.getvalue().strip(),
                          '.*\.tgz  11 / 20\.0  \(55\.00%\)')


def test_bundle_lambda(temp_folder, logcapture):
    zipfile = b'that was easy__'
    exit_code = bundle_lambda(zipfile)
    assert exit_code == 0
    assert os.path.isfile('bundle.zip')
    records = list(logcapture.actual())

    assert records[0][1] == 'INFO'
    assert records[0][2] == 'Finished - a bundle.zip is waiting for you...'


LOGS_PARAM_CASES = [
    ('2w', '1w', False, '2014-12-18 03:00:00', '2014-12-25 03:00:00'),
    ('2w', '2d', False, '2014-12-18 03:00:00', '2014-12-30 03:00:00'),
    ('2d', '2h', False, '2014-12-30 03:00:00', '2015-01-01 01:00:00'),
    ('2h', '2m', False, '2015-01-01 01:00:00', '2015-01-01 02:58:00'),
    ('20m', '1m', False, '2015-01-01 02:40:00', '2015-01-01 02:59:00'),
    ('2014-12-18 03:00:00', '2014-12-25 03:00:00', False,
        '2014-12-18 03:00:00', '2014-12-25 03:00:00'),
    (None, None, False, '2014-12-31 03:00:00', None),
    (None, None, True, '2015-01-01 02:55:00', None)
]


@pytest.mark.parametrize('start, end, tail, exp_start_ts, exp_end_ts', LOGS_PARAM_CASES)
@mock.patch('maya.now', return_value=maya.when('2015-01-01 03:00:00'))
def test_check_and_format_logs_params(mocked_maya_now, start, end, tail, exp_start_ts, exp_end_ts):
    start_ts, end_ts = check_and_format_logs_params(start, end, tail)
    assert start_ts == maya.parse(exp_start_ts).datetime(naive=True)
    if exp_end_ts is None:
        assert end_ts is None
    else:
        assert end_ts == maya.parse(exp_end_ts).datetime(naive=True)
