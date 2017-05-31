# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from pip._vendor import pkg_resources
import pip.commands.list


def get_dist(dist_name, lookup_dirs=None):
    """Get dist for installed version of dist_name avoiding pkg_resources cache
    """
    # note: based on pip/utils/__init__.py, get_installed_version(...)

    # Create a requirement that we'll look for inside of setuptools.
    req = pkg_resources.Requirement.parse(dist_name)

    # We want to avoid having this cached, so we need to construct a new
    # working set each time.
    if lookup_dirs is None:
        working_set = pkg_resources.WorkingSet()
    else:
        working_set = pkg_resources.WorkingSet(lookup_dirs)

    # Get the installed distribution from our working set
    return working_set.find(req)


def get_package_versions(package):
    """Get the package version information (=SetuptoolsVersion) which is
    comparable.
    note: we use the pip list_command implementation for this

    :param package: name of the package
    :return: installed version, latest available version
    """
    list_command = pip.commands.list.ListCommand()
    options, args = list_command.parse_args([])
    packages = [get_dist(package)]
    dists = list_command.iter_packages_latest_infos(packages, options)
    try:
        dist = next(dists)
        return dist.parsed_version, dist.latest_version
    except StopIteration:
        return None, None
