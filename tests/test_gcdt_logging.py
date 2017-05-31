# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging
from logging.config import dictConfig
from logging import getLogger, LogRecord
import textwrap
from copy import deepcopy

import pytest

from gcdt.gcdt_logging import logging_config, GcdtFormatter


def test_gcdt_logging_config_debug(capsys):
    lc = deepcopy(logging_config)
    lc['loggers']['gcdt']['level'] = 'DEBUG'
    dictConfig(lc)

    log = getLogger('gcdt.kumo_main')

    log.debug('debug message')
    log.info('info message')
    log.warning('warning message')
    log.error('error message')

    out, err = capsys.readouterr()

    assert out == textwrap.dedent("""\
        DEBUG: test_gcdt_logging: 21: debug message
        info message
        WARNING: warning message
        ERROR: error message
    """)
    # cleanup
    print(log.handlers)


def test_gcdt_logging_config_default(capsys):
    # this does not show DEBUG messages!
    dictConfig(logging_config)

    log = getLogger('gcdt.kumo_main')

    log.debug('debug message')
    log.info('info message')
    log.warning('warning message')
    log.error('error message')
    #log.error(log.handlers[0].formatter)

    out, err = capsys.readouterr()

    assert out == textwrap.dedent("""\
        info message
        WARNING: warning message
        ERROR: error message
    """)
    # assert out == textwrap.dedent("""\
    #    info message
    #    warning message
    #    error message
    # """)


def test_gcdt_formatter_info(capsys):
    rec = LogRecord('gcdt.kumo_main', logging.INFO,
                    './test_gcdt_logging.py', 26, 'info message',
                    None, None)

    assert GcdtFormatter().format(rec) == 'info message'


def test_gcdt_formatter_debug(capsys):
    rec = LogRecord('gcdt.kumo_main', logging.DEBUG,
                    './test_gcdt_logging.py', 26, 'debug message',
                    None, None)

    assert GcdtFormatter().format(
        rec) == 'DEBUG: test_gcdt_logging: 26: debug message'


def test_gcdt_formatter_error(capsys):
    rec = LogRecord('gcdt.kumo_main', logging.ERROR,
                    './test_gcdt_logging.py', 26, 'error message',
                    None, None)

    assert GcdtFormatter().format(rec) == 'ERROR: error message'


def test_gcdt_formatter_warning(capsys):
    rec = LogRecord('gcdt.kumo_main', logging.WARNING,
                    './test_gcdt_logging.py', 26, 'warning message',
                    None, None)

    assert GcdtFormatter().format(rec) == 'WARNING: warning message'


def test_log_capturing(caplog):
    # https://github.com/eisensheng/pytest-catchlog
    getLogger().info('boo %s', 'arg')

    assert caplog.record_tuples == [
        ('root', logging.INFO, 'boo arg'),
    ]
