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

from . import base
import logging

from botocore.exceptions import ClientError

LOG = logging.getLogger(__name__)


class SNSEventSource(base.EventSource):

    def __init__(self, awsclient, config):
        super(SNSEventSource, self).__init__(awsclient, config)
        self._sns = awsclient.get_client('sns')
        self._lambda = awsclient.get_client('lambda')
        self._arn = config['arn']

    def _make_notification_id(self, function_name):
        return 'Kappa-%s-notification' % function_name

    def exists(self, function):
        try:
            response = self._sns.list_subscriptions_by_topic(
                TopicArn=self._arn
            )
            LOG.debug(response)
            for subscription in response['Subscriptions']:
                if subscription['Endpoint'] == function:  #.arn:
                    return subscription
            return None
        except Exception:
            LOG.exception('Unable to find event source %s', self._arn)

    def add(self, function):
        function_name = base.get_lambda_name(function)
        try:
            response = self._sns.subscribe(
                TopicArn=self._arn, Protocol='lambda',
                Endpoint=function  #.arn
            )
            LOG.debug(response)
        except Exception:
            LOG.exception('Unable to add SNS event source')
        try:
            response = self._lambda.add_permission(
                FunctionName=function_name,
                StatementId=self._arn.split(":")[-1],
                Action='lambda:InvokeFunction',
                Principal='sns.amazonaws.com',
                SourceArn=self._arn
            )
            LOG.debug(response)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceConflictException':
                LOG.debug('Permission already exists - Continuing')
            else:
                LOG.exception('Error adding lambdaInvoke permission to SNS event source')
        except Exception:
            LOG.exception('Error adding lambdaInvoke permission to SNS event source')

    enable = add

    def update(self, function):
        self.add(function)

    def remove(self, function):
        function_name = base.get_lambda_name(function)
        LOG.debug('removing SNS event source')
        try:
            subscription = self.exists(function)
            if subscription:
                response = self._sns.unsubscribe(
                    SubscriptionArn=subscription['SubscriptionArn']
                )
                LOG.debug(response)
        except Exception:
            LOG.exception('Unable to remove event source %s', self._arn)
        try:
            response = self._lambda.remove_permission(
                FunctionName=function_name,
                StatementId=self._arn.split(":")[-1]
            )
            LOG.debug(response)
        except Exception:
            LOG.exception('Unable to remove lambda execute permission to SNS event source')

    disable = remove

    def status(self, function):
        function_name = base.get_lambda_name(function)
        LOG.debug('status for SNS notification for %s', function_name)
        status = self.exists(function)
        if status:
            status['EventSourceArn'] = status['TopicArn']
        return status
