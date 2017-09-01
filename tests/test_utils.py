# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import sys
import json
from collections import OrderedDict

import pytest

from gcdt import utils
from gcdt.utils import retries, \
    get_command, dict_merge, get_env, get_context, flatten, json2table, \
    dict_selective_merge, all_pages
from gcdt_testtools.helpers import create_tempfile, preserve_env  # fixtures!
from gcdt_testtools.helpers import logcapture  # fixtures!

from . import here

PY3 = sys.version_info[0] >= 3


# Note: version() is tested via multiple test_version_cmd in test_*_main.py


def test_retries_backoff():
    state = {'r': 0, 'h': 0, 'backoff': 2, 'tries': 5, 'mydelay': 0.1}

    def a_hook(tries_remaining, e, delay):
        assert tries_remaining == (state['tries'] - state['r'])
        assert str(e) == 'test retries!'
        assert delay == state['mydelay']
        state['mydelay'] *= state['backoff']
        state['h'] += 1

    @retries(state['tries'], delay=0.1, backoff=state['backoff'], hook=a_hook)
    def works_after_four_tries():
        state['r'] += 1
        if state['r'] < 5:
            raise Exception('test retries!')

    works_after_four_tries()
    assert state['r'] == 5


def test_retries_until_it_works():
    state = {'r': 0, 'h': 0}

    def a_hook(tries_remaining, e, delay):
        state['h'] += 1

    @retries(20, delay=0, exceptions=(ZeroDivisionError,), hook=a_hook)
    def works_after_four_tries():
        state['r'] += 1
        if state['r'] < 5:
            x = 5 / 0

    works_after_four_tries()
    assert state['r'] == 5
    assert state['h'] == 4


def test_retries_raises_exception():
    state = {'r': 0, 'h': 0, 'tries': 5}

    def a_hook(tries_remaining, e, delay):
        assert tries_remaining == (state['tries'] - state['r'])
        assert str(e) in ['division by zero',
                          'integer division or modulo by zero']
        assert delay == 0.0
        state['h'] += 1

    @retries(state['tries'], delay=0,
             exceptions=(ZeroDivisionError,), hook=a_hook)
    def never_works():
        state['r'] += 1
        x = 5 / 0

    try:
        never_works()
    except ZeroDivisionError:
        pass
    else:
        raise Exception("Failed to Raise ZeroDivisionError")

    assert state['r'] == 5
    assert state['h'] == 4


def test_command_version():
    arguments = {
        '-f': False,
        'configure': False,
        'delete': False,
        'version': True
    }
    assert get_command(arguments) == 'version'


def test_command_delete_f():
    arguments = {
        '-f': True,
        'configure': False,
        'delete': True,
        'version': False
    }
    assert get_command(arguments) == 'delete'


def test_dict_merge():
    a = {'1': 1, '2': [2], '3': {'3': 3}}
    dict_merge(a, {'3': 3})
    assert a == {'1': 1, '2': [2], '3': 3}

    dict_merge(a, {'4': 4})
    assert a == {'1': 1, '2': [2], '3': 3, '4': 4}

    dict_merge(a, {'4': {'4': 4}})
    assert a == {'1': 1, '2': [2], '3': 3, '4': {'4': 4}}

    dict_merge(a, {'4': {'5': 5}})
    assert a == {'1': 1, '2': [2], '3': 3, '4': {'4': 4, '5': 5}}

    dict_merge(a, {'2': [2, 2], '4': [4]})
    assert a == {'1': 1, '2': [2, 2], '3': 3, '4': [4]}


def test_dict_selective_merge():
    a = {'1': 1, '2': [2], '3': {'3': 3}}

    dict_selective_merge(a, {'4': 4, '5': 5}, ['5'])
    assert a == {'1': 1, '2': [2], '3': {'3': 3}, '5': 5}

    dict_selective_merge(a, {'6': 6}, ['7'])
    assert a == {'1': 1, '2': [2], '3': {'3': 3}, '5': 5}


def test_get_env(preserve_env):
    # used in cloudformation!
    os.environ['ENV'] = 'LOCAL'
    assert get_env() == 'local'

    del os.environ['ENV']
    assert get_env() == None

    os.environ['ENV'] = 'NONE_SENSE'
    assert get_env() == 'none_sense'


def test_get_context():
    context = get_context('awsclient', 'env', 'tool', 'command',
                          arguments={'foo': 'bar'})

    assert context['_awsclient'] == 'awsclient'
    assert context['env'] == 'env'
    assert context['tool'] == 'tool'
    assert context['command'] == 'command'
    assert context['_arguments'] == {'foo': 'bar'}
    assert 'gcdt-bundler' in context['plugins']
    assert 'gcdt-lookups' in context['plugins']


def test_flatten():
    actual = flatten(['junk', ['nested stuff'], [], [[]]])
    assert actual == ['junk', 'nested stuff']


# 3 tests moved from test_ramuda.py
def test_json2table():
    data = {
        'sth': 'here',
        'number': 1.1,
        'ResponseMetadata': 'bla'
    }
    expected = u'\u2552\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2564\u2550\u2550\u2550\u2550\u2550\u2550\u2555\n\u2502 sth    \u2502 here \u2502\n\u251c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u253c\u2500\u2500\u2500\u2500\u2500\u2500\u2524\n\u2502 number \u2502 1.1  \u2502\n\u2558\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2567\u2550\u2550\u2550\u2550\u2550\u2550\u255b'
    actual = json2table(data)
    assert actual == expected


def test_json2table_create_lambda_response():
    response = OrderedDict([
        ('CodeSha256', 'CwEvufZaAmNgUnlA6yTJGi8p8MNR+mNcCNYPOIwsTNM='),
        ('FunctionName', 'jenkins-gcdt-lifecycle-for-ramuda'),
        ('CodeSize', 430078),
        ('MemorySize', 256),
        ('FunctionArn',
         'arn:aws:lambda:eu-west-1:644239850139:function:jenkins-gcdt-lifecycle-for-ramuda'),
        ('Version', '13'),
        ('Role',
         'arn:aws:iam::644239850139:role/lambda/dp-dev-store-redshift-cdn-lo-LambdaCdnRedshiftLoad-DD2S84CZFGT4'),
        ('Timeout', 300),
        ('LastModified', '2016-08-23T15:27:07.658+0000'),
        ('Handler', 'handler.handle'),
        ('Runtime', 'python2.7'),
        ('Description', 'lambda test for ramuda')
    ])

    expected_file = here('resources/expected/expected_json2table.txt')
    with open(expected_file) as efile:
        expected = efile.read()
        if not PY3:
            expected = expected.decode('utf-8')
    actual = json2table(response)  # .encode('utf-8')
    assert actual == expected


def test_json2table_exception():
    data = json.dumps({
        'sth': 'here',
        'number': 1.1,
        'ResponseMetadata': 'bla'
    })
    actual = json2table(data)
    assert actual == data


def test_random_string():
    ts = utils.random_string()
    print(ts)
    assert len(ts) == 6
    assert ts != utils.random_string()


def test_random_string_length10():
    ts = utils.random_string(10)
    print(ts)
    assert len(ts) == 10
    assert ts != utils.random_string()


def test_all_pages():
    state = {'counter': 0}

    def dummy_method(**kwargs):
        # I represent the service method
        nextToken = kwargs.pop('nextToken', None)
        if nextToken:
            assert nextToken == state['counter']
        if state['counter'] < 5:
            state['counter'] += 1
            kwargs['nextToken'] = state['counter']
        return kwargs

    actual = all_pages(
        dummy_method,
        {'foo': 'bar'},
        lambda r: r['foo'] + str(r.get('nextToken', '')),
        lambda r: r.get('nextToken', 0) % 2 == 0
    )
    assert actual == ['bar2', 'bar4', 'bar']


def test_all_pages_no_condition():
    state = {'counter': 0}

    def dummy_method(**kwargs):
        # I represent the service method
        nextToken = kwargs.pop('nextToken', None)
        if nextToken:
            assert nextToken == state['counter']
        if state['counter'] < 5:
            state['counter'] += 1
            kwargs['nextToken'] = state['counter']
        return kwargs

    actual = all_pages(
        dummy_method,
        {'foo': 'bar'},
        lambda r: r['foo'] + str(r.get('nextToken', ''))
    )
    assert actual == ['bar1', 'bar2', 'bar3', 'bar4', 'bar5', 'bar']


# def all_pages(method, request, accessor, cond=None):
"""Helper to process all pages using botocore service methods (exhausts NextToken).
note: `cond` is optional... you can use it to make filtering more explicit
if you like. Alternatively you can do the filtering in the `accessor` which
is perfectly fine, too

:param method: service method
:param request: request dictionary for service call
:param accessor: function to extract data from each response
:param cond: filter function to return True / False based on a response
:return: list of collected resources
"""




# TODO get_outputs_for_stack
# TODO test_make_command
