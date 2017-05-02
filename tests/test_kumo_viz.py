# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import json
from collections import OrderedDict
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from nose.tools import assert_equal
import nose
import pytest

from gcdt.kumo_viz import cfn_viz, _analyze_sg
from . import here


def test_cfn_viz():
    template_path = here(
        'resources/sample_kumo_viz/ELBStickinessSample.template')
    dot_path = here(
        'resources/sample_kumo_viz/expected.dot')

    with open(template_path, 'r') as tfile:
        template = json.loads(tfile.read(), object_pairs_hook=OrderedDict)

    out = StringIO()
    cfn_viz(template, parameters=OrderedDict([('KeyName', 'abc123')]), out=out)

    with open(dot_path, 'r') as dfile:
        expected_dot = dfile.read()

    assert str(out.getvalue()) == expected_dot


def test_cfn_viz_problem():
    # note: this stack outputs some error message:
    # Error: trouble in init_rank
    # CdnSplitted 1
    # AMI 8
    # ...
    # this problem is already in the original code...
    # TODO: investigate this problem!
    template_path = here(
        'resources/sample_kumo_viz/problematic_stack.template')
    # dot_path = here(
    #    'resources/sample_kumo_viz/expected.dot')

    with open(template_path, 'r') as tfile:
        template = json.loads(tfile.read(), object_pairs_hook=OrderedDict)

    out = StringIO()
    cfn_viz(template, parameters={'KeyName': 'abc123'}, out=out)

    # TODO: get the expected (and correct stack output)
    # with open(dot_path, 'r') as dfile:
    #    expected_dot = dfile.read()

    # assert_equal(str(out.getvalue()), expected_dot)


def test_analyze_sg():
    template_path = here(
        'resources/sample_kumo_viz/ELBStickinessSample.template')

    with open(template_path, 'r') as tfile:
        template = json.loads(tfile.read(), object_pairs_hook=OrderedDict)

    known_sg, open_sg = _analyze_sg(template['Resources'])
    nose.tools.assert_in('InstanceSecurityGroup', known_sg)
    nose.tools.assert_in('InstanceSecurityGroup', open_sg)
