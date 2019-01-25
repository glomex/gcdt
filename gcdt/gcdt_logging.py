# -*- coding: utf-8 -*-
"""General logging support for console
"""
from __future__ import unicode_literals, print_function
import logging

from clint.packages.colorama import Fore


class GcdtFormatter(logging.Formatter):
    """Give us details in case we use DEBUG level, for INFO no details.

    For WARN and ERROR output <level>: <msg>.
    Note: gcdt does NOT have a logfile!
    """
    # http://stackoverflow.com/questions/14844970/modifying-logging-message-format-based-on-message-logging-level-in-python3
    # TODO this would be the central place to add colors. e.g. yellow for WARN
    # and red for ERROR
    # was: '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    def format(self, record):
        FORMATS = {
            logging.DEBUG: Fore.BLUE + 'DEBUG: %(module)s: %(lineno)d: %(message)s' + Fore.RESET,
            logging.INFO: '%(message)s',
            logging.WARNING: Fore.YELLOW + '%(levelname)s: %(message)s' + Fore.RESET,
            logging.ERROR: Fore.RED + '%(levelname)s: %(message)s' + Fore.RESET
        }
        format = FORMATS.get(record.levelno, "%(levelname)s: %(message)s")
        record.message = record.getMessage()
        return format % record.__dict__


# use logging.DictConfig which is the most convenient and hackable way
# to do logging configuration in Python.
logging_config = {
    'version': 1,
    'formatters': {
        'default': {
            '()': GcdtFormatter
        }
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        '': {
            'level': 'ERROR',
            'handlers': ['default'],
            'propagate': 0
        },
        '3rd_party': {
            'level': 'ERROR',
            'handlers': ['default'],
            'propagate': 0
        },
        'gcdt': {
            'level': 'INFO',
            'handlers': ['default'],
            'propagate': 0
        }
    },
    'disable_existing_loggers': False
}


def getLogger(name):
    """This is used by gcdt plugins to get a logger with the right level."""
    logger = logging.getLogger(name)
    # note: the level might be adjusted via '-v' option
    logger.setLevel(logging_config['loggers']['gcdt']['level'])
    return logger
