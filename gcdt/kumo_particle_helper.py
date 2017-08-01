# -*- coding: utf-8 -*-
""" kumo utils to use particles with troposphere.
"""
from __future__ import unicode_literals, print_function
import os

import troposphere
import troposphere.autoscaling
import troposphere.ec2
import troposphere.logs
import troposphere.s3


def initialize(template, service_name, environment='dev'):
    """Adds SERVICE_NAME, SERVICE_ENVIRONMENT, and DEFAULT_TAGS to the template

    :param template:
    :param service_name:
    :param environment:
    :return:
    """
    template.SERVICE_NAME = os.getenv('SERVICE_NAME', service_name)
    template.SERVICE_ENVIRONMENT = os.getenv('ENV', environment).lower()
    template.DEFAULT_TAGS = troposphere.Tags(**{
        'service-name': template.SERVICE_NAME,
        'environment': template.SERVICE_ENVIRONMENT
    })
    template.add_version("2010-09-09")
    template.add_description("Stack for %s microservice" % service_name)


def get_particle_permissions(particles):
    """Extract permissions from list of particles

    :param particles: list of tuples (resource, policy)
    :return: list of policies
    """
    return [p.permissions for p in particles if p.permissions is not None]


class Particle:
    """Particle class"""
    def __init__(self, template, resources, permissions=None):
        """__init__

        :param template: troposphere template
        :param resources: dictionary of resources ['resource_name']
        :param permissions: profile
        """
        self.template = template
        self.resources = resources
        self.permissions = permissions
