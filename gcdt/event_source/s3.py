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
import uuid

from botocore.client import ClientError

LOG = logging.getLogger(__name__)


class S3EventSource(base.EventSource):

    def __init__(self, awsclient, config):
        super(S3EventSource, self).__init__(awsclient, config)
        self._s3 = awsclient.get_client('s3')
        self._lambda = awsclient.get_client('lambda')

    def exists(self, lambda_arn):
        # from s3.bucket_exists:
        try:
            self._s3.head_bucket(Bucket=self._get_bucket_name())
        except ClientError:
            return False

        response = self._s3.get_bucket_notification_configuration(
            Bucket=self._get_bucket_name()
        )

        return 'LambdaFunctionConfigurations' in response

    def _make_notification_id(self, lambda_name):
        return 'gcdt-%s-notification' % lambda_name

    def _get_bucket_name(self):
        return self.arn.split(':')[-1]

    def _get_notification_spec(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        notification_spec = {
            'Id': self._make_notification_id(lambda_name),
            'Events': [e for e in self._config['events']],
            'LambdaFunctionArn': lambda_arn
        }

        # Add S3 key filters
        filter_rules = []
        # look for filter rules
        for filter_type in ['prefix', 'suffix']:
            if filter_type in self._config:
                rule = {'Name': filter_type.capitalize(), 'Value': self._config[filter_type] }
                filter_rules.append(rule)

        if filter_rules:
            notification_spec['Filter'] = {'Key': {'FilterRules': filter_rules } }
        '''
        if 'key_filters' in self._config:
            filters_spec = {'Key': {'FilterRules': [] } }
            # I do not think this is a useful structure:
            for filter in self._config['key_filters']:
                if 'type' in filter and 'value' in filter and filter['type'] in ('prefix', 'suffix'):
                    rule = {'Name': filter['type'].capitalize(), 'Value': filter['value'] }
                    filters_spec['Key']['FilterRules'].append(rule)

            notification_spec['Filter'] = filters_spec
        '''
        return notification_spec

    def add(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        alias_name = base.get_lambda_alias(lambda_arn)
        existingPermission = {}
        try:
            request = {'FunctionName': lambda_arn}
            if alias_name:
                request['Qualifer'] = alias_name
            response = self._lambda.get_policy(**request)
            existingPermission = self.arn in str(response['Policy'])
        except Exception:
            LOG.debug('S3 event source permission not available')

        if not existingPermission:
            request = {
                'FunctionName': lambda_arn,
                'StatementId': str(uuid.uuid4()),
                'Action': 'lambda:InvokeFunction',
                'Principal': 's3.amazonaws.com',
                'SourceArn': self.arn
            }
            if alias_name:
                request['Qualifer'] = alias_name
            response = self._lambda.add_permission(**request)
            LOG.debug(response)
        else:
            LOG.debug('S3 event source permission already exists')

        new_notification_spec = self._get_notification_spec(lambda_arn)

        notification_spec_list = []
        try:
            response = self._s3.get_bucket_notification_configuration(
                Bucket=self._get_bucket_name()
            )
            LOG.debug(response)
            notification_spec_list = response['LambdaFunctionConfigurations']
        except Exception as exc:
            LOG.debug('Unable to get existing S3 event source notification configurations')

        if new_notification_spec not in notification_spec_list:
            notification_spec_list.append(new_notification_spec)
        else:       
            notification_spec_list = []
            LOG.debug("S3 event source already exists")

        if notification_spec_list:

            notification_configuration = {
                'LambdaFunctionConfigurations': notification_spec_list
            }
            print(notification_configuration)

            try:
                response = self._s3.put_bucket_notification_configuration(
                    Bucket=self._get_bucket_name(),
                    NotificationConfiguration=notification_configuration
                )
                LOG.debug(response)
            except Exception as exc:
                #LOG.debug(exc.response)
                LOG.exception(exc)
                LOG.exception('Unable to add S3 event source')

    enable = add

    def update(self, lambda_arn):
        self.add(lambda_arn)

    def remove(self, lambda_arn):

        notification_spec = self._get_notification_spec(lambda_arn)

        LOG.debug('removing s3 notification')

        response = self._s3.get_bucket_notification_configuration(
            Bucket=self._get_bucket_name()
        )
        LOG.debug(response)

        if 'LambdaFunctionConfigurations' in response:
            notification_spec_list = response['LambdaFunctionConfigurations']

            if notification_spec in notification_spec_list:
                notification_spec_list.remove(notification_spec)
                response['LambdaFunctionConfigurations'] = notification_spec_list
                del response['ResponseMetadata']

                response = self._s3.put_bucket_notification_configuration(
                    Bucket=self._get_bucket_name(),
                    NotificationConfiguration=response
                )
                LOG.debug(response)

    disable = remove

    def status(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        LOG.debug('status for s3 notification for %s', lambda_name)

        notification_spec = self._get_notification_spec(lambda_arn)

        response = self._s3.get_bucket_notification_configuration(
            Bucket=self._get_bucket_name()
        )
        LOG.debug(response)

        if 'LambdaFunctionConfigurations' not in response:
            return None
        
        notification_spec_list = response['LambdaFunctionConfigurations']
        if notification_spec not in notification_spec_list:
            return None
        
        return {
            'EventSourceArn': self.arn,
            'State': 'Enabled'
        }
