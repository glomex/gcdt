# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os

from nose.tools import assert_equal
import pytest

from gcdt.utils import version, __version__, retries,  \
    get_command, dict_merge, get_env, get_context
from gcdt_testtools.helpers import create_tempfile, preserve_env  # fixtures!


def test_version(capsys):
    version()
    out, err = capsys.readouterr()
    assert out.strip().startswith('gcdt version %s' % __version__)


# would love to use logging for that...
#def test_version(caplog):
#    # https://github.com/eisensheng/pytest-catchlog
#    version()
#
#    record_tuples = list(caplog.records)
#    assert record_tuples[0].getMessage().startswith('gcdt version ')
#    assert record_tuples[0].levelno == logging.INFO


def test_retries_backoff():
    state = {'r': 0, 'h': 0, 'backoff': 2, 'tries': 5, 'mydelay': 0.1}

    def a_hook(tries_remaining, e, delay):
        assert_equal(tries_remaining, state['tries'] - state['r'])
        assert_equal(e.message, 'test retries!')
        assert_equal(delay, state['mydelay'])
        state['mydelay'] *= state['backoff']
        state['h'] += 1

    @retries(state['tries'], delay=0.1, backoff=state['backoff'], hook=a_hook)
    def works_after_four_tries():
        state['r'] += 1
        if state['r'] < 5:
            raise Exception('test retries!')

    works_after_four_tries()
    assert_equal(state['r'], 5)


def test_retries_until_it_works():
    state = {'r': 0, 'h': 0}

    def a_hook(tries_remaining, e, delay):
        state['h'] += 1

    @retries(20, delay=0, exceptions=(ZeroDivisionError,), hook=a_hook)
    def works_after_four_tries():
        state['r'] += 1
        if state['r'] < 5:
            x = 5/0

    works_after_four_tries()
    assert_equal(state['r'], 5)
    assert_equal(state['h'], 4)


def test_retries_raises_exception():
    state = {'r': 0, 'h': 0, 'tries': 5}

    def a_hook(tries_remaining, e, delay):
        assert_equal(tries_remaining, state['tries']-state['r'])
        assert_equal(e.message, 'integer division or modulo by zero')
        assert_equal(delay, 0.0)
        state['h'] += 1

    @retries(state['tries'], delay=0,
             exceptions=(ZeroDivisionError,), hook=a_hook)
    def never_works():
        state['r'] += 1
        x = 5/0

    try:
        never_works()
    except ZeroDivisionError:
        pass
    else:
        raise Exception("Failed to Raise ZeroDivisionError")

    assert_equal(state['r'], 5)
    assert_equal(state['h'], 4)


def test_command_version():
    arguments = {
        '-f': False,
        'configure': False,
        'delete': False,
        'version': True
    }
    assert_equal(get_command(arguments), 'version')


def test_command_delete_f():
    arguments = {
        '-f': True,
        'configure': False,
        'delete': True,
        'version': False
    }
    assert_equal(get_command(arguments), 'delete')


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


# TODO get_outputs_for_stack
# TODO test_make_command

