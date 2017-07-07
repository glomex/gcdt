# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os

from gcdt_testtools.helpers_aws import recorder, file_reader, awsclient, \
    check_playback_mode
from gcdt_testtools.helpers import temp_folder  # fixture!
from gcdt_testtools import helpers
from . import here


def test_recorder(temp_folder):
    c = {'x': 100}

    def fake_func():
        c['x'] += 1
        return c['x']

    wrapped = recorder(temp_folder[0], fake_func)
    wrapped()
    wrapped()
    with open(os.path.join(temp_folder[0], 'fake_func'), 'r') as rfile:
        body = ''.join(rfile.readlines())
        assert body == '101\n102\n'


def test_file_reader(temp_folder):
    filename = os.path.join(temp_folder[0], 'fake_data_file')
    with open(filename, 'w') as dfile:
        print('111', file=dfile)
        print('222', file=dfile)

    with open(filename, 'r') as dfile:
        reader = file_reader(temp_folder[0], 'fake_data_file')
        assert reader() == '111'
        assert reader() == '222'


def test_file_reader_with_datatype_int(temp_folder):
    filename = os.path.join(temp_folder[0], 'fake_data_file')
    with open(filename, 'w') as dfile:
        print('111', file=dfile)
        print('222', file=dfile)

    with open(filename, 'r') as dfile:
        reader = file_reader(temp_folder[0], 'fake_data_file', 'int')
        assert reader() == 111
        assert reader() == 222


@check_playback_mode
def test_random_string_recording(awsclient):
    # record and playback cases are identical for this test
    lines = []
    for i in range(5):
        lines.append(helpers.random_string())

    prefix = 'tests.test_helpers_aws.test_random_string_recording'
    record_dir = os.path.join(here('./resources/placebo_awsclient'), prefix)
    random_string_filename = 'random_string.txt'
    with open(os.path.join(record_dir, random_string_filename), 'r') as rfile:
        rlines = [l.strip() for l in rfile.readlines()]

        assert lines == rlines
