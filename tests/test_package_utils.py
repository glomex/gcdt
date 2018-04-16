# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import mock
from pip._vendor import pkg_resources
from pip._internal.commands.list import ListCommand

from gcdt.package_utils import get_dist, get_package_versions

from gcdt_testtools.helpers import Bunch


def test_get_dist():
    fake_gcdt = pkg_resources.EggInfoDistribution(
        location='/Users/fin0007m/devel/gcdt/glomex-cloud-deployment-tools',
        metadata=None, project_name='gcdt', version='0.0.77')
    fake_ws = pkg_resources.WorkingSet()
    fake_ws.by_key = {'gcdt': fake_gcdt}

    with mock.patch('pip._vendor.pkg_resources.WorkingSet', return_value=fake_ws):
        assert get_dist('gcdt').version == '0.0.77'


def test_get_package_versions():
    ipli = iter([Bunch(parsed_version='0.0.77', latest_version='0.0.88')])

    with mock.patch.object(ListCommand,
                           'iter_packages_latest_infos',
                           return_value=ipli):
        installed_version, latest_available_version = get_package_versions('gcdt')
        assert installed_version == '0.0.77'
        assert latest_available_version == '0.0.88'


def test_get_package_versions_not_installed():
    ipli = iter([])

    with mock.patch.object(ListCommand,
                           'iter_packages_latest_infos',
                           return_value=ipli):
        installed_version, latest_available_version = \
            get_package_versions('not_installed')
        assert installed_version is None
        assert latest_available_version is None
