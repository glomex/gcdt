# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import pytest
import regex
import logging

from gcdt.kumo_main import version_cmd, list_cmd, preview_cmd, dot_cmd, \
    generate_cmd, deploy_cmd, delete_cmd, load_template
from gcdt.kumo_core import _get_stack_state

from gcdt_testtools.helpers_aws import check_preconditions, get_tooldata
from gcdt_testtools.helpers import check_dot_precondition
from gcdt_testtools.helpers_aws import awsclient  # fixtures!
from .test_kumo_aws import simple_cloudformation_stack  # fixtures!
from .test_kumo_aws import simple_cloudformation_stack_folder  # fixtures!
from .test_kumo_aws import sample_ec2_cloudformation_stack_folder  # fixtures!
from gcdt_testtools.helpers import temp_folder  # fixtures!
from . import here


# note: xzy_main tests have a more "integrative" character so focus is to make
# sure that the gcdt parts fit together not functional coverage of the parts.


def test_load_template(capsys):
    """Bail out if template is not found.
    """
    with pytest.raises(SystemExit):
        load_template()
    out, err = capsys.readouterr()
    assert 'no cloudformation.py found, bailing out...\n' in out


def test_version_cmd(capsys):
    version_cmd()
    out, err = capsys.readouterr()
    assert out.startswith('gcdt version')


@pytest.mark.aws
@check_preconditions
def test_list_cmd(awsclient, capsys):
    tooldata = get_tooldata(
        awsclient, 'kumo', 'list',
        config_base_name='gcdt_large',
        location=here('./resources/simple_cloudformation_stack/'))
    list_cmd(**tooldata)
    out, err = capsys.readouterr()
    # using regular expression search in captured output
    assert regex.search('listed \d+ stacks', out) is not None


@pytest.mark.aws
@check_preconditions
def test_preview_cmd(awsclient, simple_cloudformation_stack,
                     simple_cloudformation_stack_folder, capsys):
    tooldata = get_tooldata(
        awsclient, 'kumo', 'preview',
        config_base_name='gcdt_large',
        location=here('./resources/simple_cloudformation_stack/'))
    preview_cmd(**tooldata)
    out, err = capsys.readouterr()
    # verify diff results
    assert 'InstanceType │ t2.micro      │ t2.medium ' in out


@pytest.mark.aws
@check_preconditions
@check_dot_precondition
def test_dot_cmd(awsclient, sample_ec2_cloudformation_stack_folder):
    tooldata = get_tooldata(awsclient, 'kumo', 'dot')
    assert dot_cmd(**tooldata) == 0
    assert os.path.exists('cloudformation.svg')
    os.unlink('cloudformation.svg')


@pytest.mark.aws
@check_preconditions
def test_generate_cmd(awsclient, simple_cloudformation_stack_folder):
    tooldata = get_tooldata(awsclient, 'kumo', 'generate')
    assert generate_cmd(**tooldata) == 0
    filename = 'infra-dev-kumo-sample-stack-generated-cf-template.json'
    assert os.path.exists(filename)
    os.unlink(filename)


@pytest.mark.aws
@check_preconditions
def test_deploy_delete_cmds(awsclient, simple_cloudformation_stack_folder):
    tooldata = get_tooldata(awsclient, 'kumo', 'deploy')
    assert deploy_cmd(False, **tooldata) == 0
    assert _get_stack_state(awsclient.get_client('cloudformation'),
                            'infra-dev-kumo-sample-stack') in ['CREATE_COMPLETE']
    tooldata['context']['command'] = 'delete'
    assert delete_cmd(True, **tooldata) == 0
    assert _get_stack_state(awsclient.get_client('cloudformation'),
                            'infra-dev-kumo-sample-stack') is None
