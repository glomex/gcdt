# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging

from . import base
from ..ramuda_utils import all_pages


LOG = logging.getLogger(__name__)


class CloudFrontEventSource(base.EventSource):

    def __init__(self, awsclient, config):
        super(CloudFrontEventSource, self).__init__(awsclient, config)
        self._cloudfront = awsclient.get_client('cloudfront')
        self._lambda = awsclient.get_client('lambda')
        # _config in base!

    def exists(self, lambda_arn):
        LOG.debug('executing check whether distribution \'%s\' exists' % self._get_distribution_id())
        distribution_config, _ = self._get_distribution_config()
        if distribution_config is not None:
            LOG.debug('distribution exists')
            return True
        return False

    def _get_distribution_id(self):
        distribution = self.arn.split(':')[-1]
        assert distribution.startswith('distribution/')
        return distribution[13:]

    def _get_last_published_lambda_version(self, lambda_arn):
        version = max(all_pages(
            self._lambda.list_versions_by_function,
            {'FunctionName': base.get_lambda_name(lambda_arn)},
            lambda resp: [int(v['Version']) for v in resp['Versions']
                          if v['Version'] != '$LATEST']
        ))

        lambda_version_arn = lambda_arn.split(':')
        lambda_version_arn[7] = str(version)
        return ':'.join(lambda_version_arn[:])

    def _get_distribution_config(self):
        try:
            response = self._cloudfront.get_distribution_config(Id=self._get_distribution_id())
            return response['DistributionConfig'], response['ETag']
        except Exception as exc:
            LOG.exception(exc)
            LOG.exception('Unable to read distribution config')

    def _is_same_trigger(self, trigger_1, trigger_2):
        base_lambda_arn_1 = base.get_lambda_basearn(trigger_1['LambdaFunctionARN'])
        base_lambda_arn_2 = base.get_lambda_basearn(trigger_2['LambdaFunctionARN'])
        return base_lambda_arn_1 == base_lambda_arn_2 and trigger_1['EventType'] == trigger_2['EventType']

    def add(self, lambda_arn):
        distribution_config, etag = self._get_distribution_config()
        request = {
            'DistributionConfig': distribution_config,
            'Id': self._get_distribution_id(),
            'IfMatch': etag
        }

        new_trigger = {
            'LambdaFunctionARN': self._get_last_published_lambda_version(lambda_arn),
            'EventType': self._config['cloudfront_event']
        }

        new_triggers = []
        current_triggers_object = request['DistributionConfig']['DefaultCacheBehavior']['LambdaFunctionAssociations']
        if 'Items' in current_triggers_object:
            current_triggers = current_triggers_object['Items']
        else:
            current_triggers = []
        for trigger in current_triggers:
            if not self._is_same_trigger(trigger, new_trigger):
                new_triggers.append(trigger)
        new_triggers.append(new_trigger)

        request['DistributionConfig']['DefaultCacheBehavior']['LambdaFunctionAssociations'] = {
            'Quantity': len(new_triggers),
            'Items': new_triggers
        }

        try:
            response = self._cloudfront.update_distribution(
                **request
            )
            LOG.debug(response)
        except Exception as exc:
            LOG.exception(exc)
            LOG.exception('Unable to add lambda trigger')

    enable = add

    def update(self, lambda_arn):
        self.add(lambda_arn)

    def remove(self, lambda_arn):
        distribution_config, etag = self._get_distribution_config()
        request = {
            'DistributionConfig': distribution_config,
            'Id': self._get_distribution_id(),
            'IfMatch': etag
        }
        # add empty lambda-trigger to DistributionConfig
        request['DistributionConfig']['DefaultCacheBehavior']['LambdaFunctionAssociations'] = {
            'Quantity': 0
        }

        try:
            response = self._cloudfront.update_distribution(
                **request
            )
            LOG.debug(response)
        except Exception as exc:
            LOG.exception(exc)
            LOG.exception('Unable to remove lambda trigger')

    disable = remove

    def status(self, lambda_arn):
        LOG.debug('status for lambda trigger for distribution %s',
                  self._get_distribution_id())
        status = self.exists(lambda_arn)
        return status
