# -*- coding: utf-8 -*-
"""Simplified AWSClient.
This module abstracts the botocore session and clients
to provide a simpler interface.
"""
from __future__ import unicode_literals, print_function
from botocore.exceptions import ClientError  # used in plugins -> keep!!


class AWSClient(object):
    # note this is heavily inspired by TypedAWSClient:
    # https://github.com/awslabs/chalice/blob/master/chalice/awsclient.py
    def __init__(self, session):
        self._session = session
        self._client_cache = {}

    def get_client(self, service_name, region_name=None, **kwargs):
        if region_name is None:
            # use the region from the session
            region_name = self._session.get_config_variable('region')

        if (service_name, region_name) not in self._client_cache:
            self._client_cache[(service_name, region_name)] = \
                self._session.create_client(service_name, region_name, **kwargs)
        return self._client_cache[(service_name, region_name)]

    def get_region(self):
        """Get region from the session."""
        return self._session.get_config_variable('region')

    def get_account_id(self):
        """Get account id using session."""
        sts = self.get_client('sts')
        return sts.get_caller_identity()["Account"]
