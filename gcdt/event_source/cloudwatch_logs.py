from __future__ import unicode_literals, print_function

import os
from time import sleep

import logging

from botocore.exceptions import ClientError

from . import base

LOG = logging.getLogger(__name__)


class CloudWatchLogsEventSource(base.EventSource):
    def __init__(self, awsclient, config):
        super(CloudWatchLogsEventSource, self).__init__(awsclient, config)

        self._logs = awsclient.get_client('logs')
        self._lambda = awsclient.get_client('lambda')

        self._log_group_name_prefix = config['log_group_name_prefix']
        self._filter_name = config['filter_name']

    def exists(self, _lambda_arn):
        return True

    def add(self, lambda_arn):
        current_lambda_log_group_name = {"/aws/lambda/%s" % base.get_lambda_name(lambda_arn)}

        all_log_group_names = self._log_group_names_by_prefix(None) - current_lambda_log_group_name
        LOG.debug("all log groups: %s" % ", ".join(all_log_group_names))

        group_names_by_prefix = self._log_group_names_by_prefix(self._log_group_name_prefix) - current_lambda_log_group_name
        LOG.debug("log groups by prefix: %s" % ", ".join(group_names_by_prefix))

        log_group_names_to_remove_subscriptions = all_log_group_names - group_names_by_prefix
        LOG.debug("log groups to remove subscriptions: %s" % ", ".join(group_names_by_prefix))

        for log_group_name in log_group_names_to_remove_subscriptions:
            if self._log_group_subscribed_to_lambda(lambda_arn, log_group_name):
                self._remove_log_group_subscription_to_lambda(lambda_arn, log_group_name)

        self._ensure_cloudwatch_permissions(lambda_arn)

        for log_group_name in group_names_by_prefix:
            if not self._log_group_subscribed_to_lambda(lambda_arn, log_group_name):
                self._subscribe_log_group_to_lambda(lambda_arn, log_group_name)

        return True

    def update(self, lambda_arn):
        return self.add(lambda_arn)

    def remove(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        alias_name = base.get_lambda_alias(lambda_arn)

        LOG.debug("removing lambda policy")
        self._sleep()
        self._lambda.remove_permission(FunctionName=lambda_name,
                                       Qualifier=alias_name,
                                       StatementId=self._filter_name)

        group_names_by_prefix = self._log_group_names_by_prefix(None)
        for log_group_name in group_names_by_prefix:
            if self._log_group_subscribed_to_lambda(lambda_arn, log_group_name):
                self._remove_log_group_subscription_to_lambda(lambda_arn, log_group_name)

        return True

    def _log_group_names_by_prefix(self, prefix):
        kwargs = {}
        if prefix:
            kwargs = {"logGroupNamePrefix": prefix}

        self._sleep()
        log_groups = self._logs.describe_log_groups(**kwargs)
        log_group_names = _extract_names_from_log_groups(log_groups)

        while 'nextToken' in log_groups:
            self._sleep()
            log_groups = self._logs.describe_log_groups(nextToken=log_groups['nextToken'], **kwargs)
            log_group_names |= _extract_names_from_log_groups(log_groups)

        return log_group_names

    def _log_group_subscribed_to_lambda(self, lambda_arn, log_group_name):
        self._sleep()
        subscription_filters = self._logs.describe_subscription_filters(logGroupName=log_group_name)
        return any(map(lambda e: e['filterName'] == self._filter_name,
                       subscription_filters['subscriptionFilters']))

    def _subscribe_log_group_to_lambda(self, lambda_arn, log_group_name):
        self._sleep()
        LOG.debug("adding subscription for %s" % log_group_name)
        return self._logs.put_subscription_filter(logGroupName=log_group_name,
                                                  destinationArn=lambda_arn,
                                                  filterName=self._filter_name,
                                                  filterPattern="",
                                                  distribution="ByLogStream")

    def _remove_log_group_subscription_to_lambda(self, lambda_arn, log_group_name):
        self._sleep()
        LOG.debug("removing subscription for %s" % log_group_name)
        return self._logs.delete_subscription_filter(logGroupName=log_group_name,
                                                     filterName=self._filter_name)

    def _ensure_cloudwatch_permissions(self, lambda_arn):
        lambda_name = base.get_lambda_name(lambda_arn)
        alias_name = base.get_lambda_alias(lambda_arn)

        account_id = lambda_arn.split(":")[4]
        arn_like = "arn:aws:logs:eu-west-1:%s:log-group:%s*:*" % (account_id, self._log_group_name_prefix)

        try:
            self._sleep()
            self._lambda.remove_permission(FunctionName=lambda_name,
                                           Qualifier=alias_name,
                                           StatementId=self._filter_name)
        except ClientError:
            pass

        LOG.debug("updating lambda policy allowing access for %s" % arn_like)
        self._sleep()
        self._lambda.add_permission(FunctionName=lambda_name,
                                    Qualifier=alias_name,
                                    StatementId=self._filter_name,
                                    Action="lambda:InvokeFunction",
                                    Principal="logs.eu-west-1.amazonaws.com",
                                    SourceArn=arn_like)

    def _sleep(self):
        aws_requests_sleep = float(os.environ.get('AWS_REQUESTS_SLEEP', '0'))
        sleep(aws_requests_sleep)


def _extract_names_from_log_groups(log_groups):
    return {lg['logGroupName'] for lg in log_groups['logGroups']}
