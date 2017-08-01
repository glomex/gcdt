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

from . import base
import logging

from botocore.exceptions import ClientError

LOG = logging.getLogger(__name__)


class SNSEventSource(base.EventSource):

    def __init__(self, awsclient, config):
        super(SNSEventSource, self).__init__(awsclient, config)
        self._sns = awsclient.get_client('sns')
        self._lambda = awsclient.get_client('lambda')

    def _make_notification_id(self, lambda_name):
        return 'gcdt-%s-notification' % lambda_name

    def exists(self, lambda_arn):
        try:
            response = self._sns.list_subscriptions_by_topic(
                TopicArn=self.arn
            )
            LOG.debug(response)
            for subscription in response['Subscriptions']:
                if subscription['Endpoint'] == lambda_arn:
                    return subscription
        except Exception:
            LOG.exception('Unable to find event source %s', self.arn)
        return None

    def add(self, lambda_arn):
        alias_name = base.get_lambda_alias(lambda_arn)
        try:
            response = self._sns.subscribe(
                TopicArn=self.arn, Protocol='lambda',
                Endpoint=lambda_arn
            )
            LOG.debug(response)
        except Exception:
            LOG.exception('Unable to add SNS event source')
        try:
            request = {
                'FunctionName': lambda_arn,
                'StatementId': self.arn.split(":")[-1],
                'Action': 'lambda:InvokeFunction',
                'Principal': 'sns.amazonaws.com',
                'SourceArn': self.arn
            }
            if alias_name:
                request['Qualifer'] = alias_name
            response = self._lambda.add_permission(**request)
            LOG.debug(response)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceConflictException':
                LOG.debug('Permission already exists - Continuing')
            else:
                LOG.exception('Error adding lambdaInvoke permission to SNS event source')
        except Exception:
            LOG.exception('Error adding lambdaInvoke permission to SNS event source')

    enable = add

    def update(self, lambda_arn):
        self.add(lambda_arn)

    def remove(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        alias_name = base.get_lambda_alias(lambda_arn)
        LOG.debug('removing SNS event source')
        try:
            subscription = self.exists(lambda_arn)
            if subscription:
                response = self._sns.unsubscribe(
                    SubscriptionArn=subscription['SubscriptionArn']
                )
                LOG.debug(response)
        except Exception:
            LOG.exception('Unable to remove event source %s', self.arn)
        try:
            request = {
                'FunctionName': lambda_name,
                'StatementId': self.arn.split(":")[-1]
            }
            if alias_name:
                request['Qualifer'] = alias_name
            response = self._lambda.remove_permission(**request)
            LOG.debug(response)
        except Exception:
            LOG.exception('Unable to remove lambda execute permission to SNS event source')

    disable = remove

    def status(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        LOG.debug('status for SNS notification for %s', lambda_name)
        status = self.exists(lambda_arn)
        if status:
            status['EventSourceArn'] = status['TopicArn']
        return status
