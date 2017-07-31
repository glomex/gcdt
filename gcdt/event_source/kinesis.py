# -*- coding: utf-8 -*-
# Copyright (c) 2014, 2015 Mitch Garnaat
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import unicode_literals, print_function

import botocore.exceptions
from . import base
import logging

LOG = logging.getLogger(__name__)


class KinesisEventSource(base.EventSource):

    def __init__(self, awsclient, config):
        super(KinesisEventSource, self).__init__(awsclient, config)
        self._lambda = awsclient.get_client('lambda')

    def exists(self, lambda_arn):
        return self._get_uuid(lambda_arn)

    def _get_uuid(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        uuid = None
        response = self._lambda.list_event_source_mappings(
            FunctionName=lambda_name,
            EventSourceArn=self.arn
        )
        LOG.debug(response)
        if len(response['EventSourceMappings']) > 0:
            uuid = response['EventSourceMappings'][0]['UUID']
        return uuid

    def add(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        try:
            response = self._lambda.create_event_source_mapping(
                FunctionName=lambda_name,
                EventSourceArn=self.arn,
                BatchSize=self.batch_size,
                StartingPosition=self.starting_position,
                Enabled=self.enabled
            )
            LOG.debug(response)
        except Exception:
            LOG.exception('Unable to add event source')

    def enable(self, lambda_arn):
        self._config['enabled'] = True
        try:
            response = self._lambda.update_event_source_mapping(
                UUID=self._get_uuid(lambda_arn),
                Enabled=self.enabled
            )
            LOG.debug(response)
        except Exception:
            LOG.exception('Unable to enable event source')

    def disable(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        self._config['enabled'] = False
        try:
            response = self._lambda.update_event_source_mapping(
                FunctionName=lambda_name,
                Enabled=self.enabled
            )
            LOG.debug(response)
        except Exception:
            LOG.exception('Unable to disable event source')

    def update(self, lambda_arn):
        response = None
        uuid = self._get_uuid(lambda_arn)
        if uuid:
            try:
                response = self._lambda.update_event_source_mapping(
                    BatchSize=self.batch_size,
                    Enabled=self.enabled,
                    FunctionName=lambda_arn)
                LOG.debug(response)
            except Exception:
                LOG.exception('Unable to update event source')

    def remove(self, lambda_arn):
        response = None
        uuid = self._get_uuid(lambda_arn)
        if uuid:
            response = self._lambda.delete_event_source_mapping(UUID=uuid)
            LOG.debug(response)
        return response

    def status(self, lambda_arn):
        response = None
        LOG.debug('getting status for event source %s', self.arn)
        uuid = self._get_uuid(lambda_arn)
        if uuid:
            try:
                response = self._lambda.get_event_source_mapping(
                    UUID=self._get_uuid(lambda_arn)
                )
                LOG.debug(response)
            except botocore.exceptions.ClientError:
                LOG.debug('event source %s does not exist', self.arn)
                response = None
        else:
            LOG.debug('No UUID for event source %s', self.arn)
        return response
