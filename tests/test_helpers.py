# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import os
from nose.tools import assert_equal

from gcdt_testtools.helpers import create_tempfile, get_size
from gcdt_testtools.helpers import temp_folder  # fixtures!


def test_create_tempfile():
    tf = create_tempfile('blah\nblub\n')
    with open(tf, 'r') as tfile:
        contents = tfile.read()
        assert_equal(contents, 'blah\nblub\n')
    # cleanup the tempfile
    os.unlink(tf)


def test_get_size(temp_folder):
    # prepare two files to read the size
    with open('tmp1.txt', 'w')as t1:
        t1.write('some\nstuff\n    \nhere\n')
    with open('tmp2.txt', 'w')as t2:
        t2.write('some\nmore stuff\n    \nhere\n')

    size = get_size()
    assert_equal(size, 47)


# TODO: write test for check_preconditions!
