# -*- coding: utf-8 -*-
"""Simplified AWSClient.
This module abstracts the botocore session and clients
to provide a simpler interface.
"""
from __future__ import unicode_literals, print_function
from botocore.exceptions import ClientError  # used in plugins


class AWSClient(object):
    # note this is heavily inspired by TypedAWSClient:
    # https://github.com/awslabs/chalice/blob/master/chalice/awsclient.py
    def __init__(self, session):
        self._session = session
        self._client_cache = {}

    def get_client(self, service_name):
        if service_name not in self._client_cache:
            self._client_cache[service_name] = self._session.create_client(
                service_name)
        return self._client_cache[service_name]
