# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
from datetime import datetime

from gcdt.servicediscovery import parse_ts
import pytest


def test_parse_ts():
    assert parse_ts('2016-06-22T06:51:59.000Z') == \
        datetime(2016, 6, 22, 6, 51, 59, 0)
