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

    def _is_same_lambda_association(self, association_1, association_2):
        base_lambda_arn_1 = base.get_lambda_basearn(association_1['LambdaFunctionARN'])
        base_lambda_arn_2 = base.get_lambda_basearn(association_2['LambdaFunctionARN'])
        return base_lambda_arn_1 == base_lambda_arn_2 and association_1['EventType'] == association_2['EventType']

    def add(self, lambda_arn):
        distribution_config, etag = self._get_distribution_config()
        request = {
            'DistributionConfig': distribution_config,
            'Id': self._get_distribution_id(),
            'IfMatch': etag
        }

        new_lambda_association = {
            'LambdaFunctionARN': self._get_last_published_lambda_version(lambda_arn),
            'EventType': self._config['cloudfront_event']
        }

        new_lambda_associations = []
        current_lambda_associations = request['DistributionConfig']['DefaultCacheBehavior']['LambdaFunctionAssociations']['Items']
        for lambda_association in current_lambda_associations:
            if not self._is_same_lambda_association(lambda_association, new_lambda_association):
                new_lambda_associations.append(lambda_association)
        new_lambda_associations.append(new_lambda_association)

        request['DistributionConfig']['DefaultCacheBehavior']['LambdaFunctionAssociations'] = {
            'Quantity': len(new_lambda_associations),
            'Items': new_lambda_associations
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
