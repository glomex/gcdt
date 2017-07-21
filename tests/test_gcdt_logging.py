# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging
from logging import getLogger, LogRecord

import pytest
#from testfixtures import LogCapture
from clint.packages.colorama import Fore

from gcdt.gcdt_logging import logging_config, GcdtFormatter
from gcdt_testtools.helpers import logcapture  # fixture!


# cleanup of the log config does not yet work so we can not run
# any tests that use realistic log configs
'''
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
        DEBUG: test_gcdt_logging: 22: debug message
        info message
        WARNING: warning message
        ERROR: error message
    """)
    # cleanup
    print(log.handlers)
'''


# cleanup of the log config does not yet work so we can not run
# any tests that use realistic log configs
'''
def test_gcdt_logging_config_debug():
    lc = deepcopy(logging_config)
    lc['loggers']['gcdt']['level'] = 'DEBUG'
    dictConfig(lc)

    log = getLogger('gcdt.kumo_main')

    with LogCapture() as l:
        log.debug('debug message')
        log.info('info message')
        log.warning('warning message')
        log.error('error message')

        records = list(l.actual())
        assert records[0] == ('root', 'DEBUG', 'test_gcdt_logging: 22: debug message')

    #out, err = capsys.readouterr()

    #assert out == textwrap.dedent("""\
    #    DEBUG: test_gcdt_logging: 22: debug message
    #    info message
    #    WARNING: warning message
    #    ERROR: error message
    #""")
    # cleanup
    #print(log.handlers)
'''


# cleanup of the log config does not yet work so we can not run
# any tests that use realistic log configs
'''
def test_gcdt_logging_config_default(capsys):
    # this does not show DEBUG messages!
    dictConfig(logging_config)

    log = getLogger('gcdt.kumo_main')

    log.debug('debug message')
    log.info('info message')
    log.warning('warning message')
    log.error('error message')

    out, err = capsys.readouterr()

    assert out == textwrap.dedent("""\
        info message
        WARNING: warning message
        ERROR: error message
    """)
'''


def test_gcdt_formatter_info(capsys):
    rec = LogRecord('gcdt.kumo_main', logging.INFO,
                    './test_gcdt_logging.py', 26, 'info message',
                    None, None)

    assert GcdtFormatter().format(rec) == 'info message'


def test_gcdt_formatter_debug(capsys):
    rec = LogRecord('gcdt.kumo_main', logging.DEBUG,
                    './test_gcdt_logging.py', 26, 'debug message',
                    None, None)

    assert GcdtFormatter().format(rec) == \
           Fore.BLUE + 'DEBUG: test_gcdt_logging: 26: debug message' + Fore.RESET


def test_gcdt_formatter_error(capsys):
    rec = LogRecord('gcdt.kumo_main', logging.ERROR,
                    './test_gcdt_logging.py', 26, 'error message',
                    None, None)

    assert GcdtFormatter().format(rec) == \
           Fore.RED + 'ERROR: error message' + Fore.RESET


def test_gcdt_formatter_warning(capsys):
    rec = LogRecord('gcdt.kumo_main', logging.WARNING,
                    './test_gcdt_logging.py', 26, 'warning message',
                    None, None)

    assert GcdtFormatter().format(rec) == \
           Fore.YELLOW + 'WARNING: warning message' + Fore.RESET


def test_log_capturing(logcapture):
    getLogger().info('boo %s', 'arg')
    assert list(logcapture.actual()) == [
        ('root', 'INFO', 'boo arg'),
    ]
