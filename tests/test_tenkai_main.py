# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import os
import logging

import pytest

from gcdt.tenkai_main import version_cmd, deploy_cmd, bundle_cmd
from gcdt_bundler.bundler import bundle_revision

from gcdt_testtools.helpers_aws import check_preconditions, get_tooldata
from gcdt_testtools.helpers_aws import awsclient  # fixtures !
from .test_tenkai_aws import sample_codedeploy_app  # fixtures !
from gcdt_testtools.helpers import logcapture  # fixtures!
from . import here


# note: xzy_main tests have a more "integrative" character so focus is to make
# sure that the gcdt parts fit together not functional coverage of the parts.


@pytest.fixture(scope='function')  # 'function' or 'module'
def simple_codedeploy_folder():
    # helper to get into the sample folder so kumo can find cloudformation.py
    cwd = (os.getcwd())
    os.chdir(here('./resources/simple_codedeploy/'))
    yield
    # cleanup
    os.chdir(cwd)  # cd back to original folder


@pytest.fixture(scope='function')  # 'function' or 'module'
def sample_codedeploy_app_working_folder():
    # helper to get into the sample folder so kumo can find cloudformation.py
    cwd = (os.getcwd())
    os.chdir(here('./resources/sample_codedeploy_app/working/'))
    yield
    # cleanup
    os.chdir(cwd)  # cd back to original folder


def test_version_cmd(logcapture):
    version_cmd()
    records = list(logcapture.actual())

    assert records[0][1] == 'INFO'
    assert records[0][2].startswith('gcdt version ')
    assert records[1][1] == 'INFO'
    assert (records[1][2].startswith('gcdt plugins:') or
            records[1][2].startswith('gcdt tools:'))


@pytest.mark.aws
@check_preconditions
def test_deploy_cmd(awsclient, sample_codedeploy_app,
                    sample_codedeploy_app_working_folder):
    tooldata = get_tooldata(awsclient, 'tenkai', 'deploy')
    # gcdt-plugins are installed anyway so this is ok
    # TODO alternatively prepare a stock bundle.zip!
    folders = [{'source': 'codedeploy', 'target': ''}]
    tooldata['context']['_bundle_file'] = bundle_revision(folders)
    deploy_cmd(**tooldata)


def test_bundle_cmd(logcapture):
    tooldata = {
        'context': {'_bundle_file': 'test_file'}
    }
    bundle_cmd(**tooldata)
    records = list(logcapture.actual())
    assert records[0][1] == 'INFO'
    assert records[0][2].startswith('created bundle at test_file')
