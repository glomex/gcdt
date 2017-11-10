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
import logging
import uuid
import json

from . import base


LOG = logging.getLogger(__name__)


class CloudWatchEventSource(base.EventSource):

    def __init__(self, awsclient, config):
        super(CloudWatchEventSource, self).__init__(awsclient, config)
        self._events = awsclient.get_client('events')
        self._lambda = awsclient.get_client('lambda')
        if 'name' in config:
            self._name = config['name']
        else:
            raise ValueError('\'name\' attribute missing from event_source')

    def exists(self, lambda_arn):
        return self.get_rule()

    def get_rule(self):
        response = self._events.list_rules(NamePrefix=self._name)
        LOG.debug(response)
        if 'Rules' in response:
            for r in response['Rules']:
                if r['Name'] == self._name:
                    return r
        return None

    def add(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        alias_name = base.get_lambda_alias(lambda_arn)
        kwargs = {
            'Name': self._name,
            'State': 'ENABLED' if self.enabled else 'DISABLED'
        }
        if 'schedule' in self._config:
            kwargs['ScheduleExpression'] = self._config['schedule']
        if 'pattern' in self._config:
            kwargs['EventPattern'] = json.dumps(self._config['pattern'])
        if 'description' in self._config:
            kwargs['Description'] = self._config['description']
        if 'role_arn' in self._config:
            kwargs['RoleArn'] = self._config['role_arn']
        try:
            LOG.debug(kwargs)
            response = self._events.put_rule(**kwargs)
            LOG.debug(response)
            self._config['arn'] = response['RuleArn']
            existingPermission={}
            try:
                request = {'FunctionName': lambda_arn}
                if alias_name:
                    request['Qualifer'] = alias_name
                response = self._lambda.get_policy(**request)
                existingPermission = self._config['arn'] in str(response['Policy'])
            except Exception:
                LOG.debug('CloudWatch event source permission not available')

            if not existingPermission:
                request = {
                    'FunctionName': lambda_arn,
                    'StatementId': str(uuid.uuid4()),
                    'Action': 'lambda:InvokeFunction',
                    'Principal': 'events.amazonaws.com',
                    'SourceArn': self.arn
                }
                if alias_name:
                    request['Qualifer'] = alias_name
                response = self._lambda.add_permission(**request)
                LOG.debug(response)
            else:
                LOG.debug('CloudWatch event source permission already exists')

            target = {
                'Id': lambda_name,
                'Arn': lambda_arn
            }
            if 'input_path' in self._config:
                target['InputPath'] = self._config['input_path']

            response = self._events.put_targets(
                 Rule=self._name,
                 Targets=[target]
            )
            LOG.debug(response)
        except Exception as e:
            LOG.exception('Unable to put CloudWatch event source: %s' % e.message)

    def update(self, lambda_arn):
        self.add(lambda_arn)

    def remove(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        LOG.debug('removing CloudWatch event source')
        try:
            rule = self.get_rule()
            if rule:
                response = self._events.remove_targets(
                    Rule=self._name,
                    Ids=[lambda_name]
                )
                LOG.debug(response)
                response = self._events.delete_rule(Name=self._name)
                LOG.debug(response)
        except Exception:
            LOG.exception('Unable to remove CloudWatch event source %s', self._name)

    def status(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        LOG.debug('status for CloudWatch event for %s', lambda_name)
        return self._to_status(self.get_rule())

    def enable(self, lambda_arn):
        if self.get_rule():
            self._events.enable_rule(Name=self._name)

    def disable(self, lambda_arn):
        if self.get_rule():
            self._events.disable_rule(Name=self._name)

    def _to_status(self, rule):
        if rule:
            return {
                'EventSourceArn': rule['Arn'],
                'State': rule['State']
            }
        return None
