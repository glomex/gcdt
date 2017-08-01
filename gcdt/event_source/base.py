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
from copy import deepcopy


def get_lambda_name(lambda_arn):
    # in case we need the lambda name, we use this helper function
    parts = lambda_arn.split(':')
    return parts[6]


def get_lambda_alias(lambda_arn):
    # in case we need the lambda name, we use this helper function
    parts = lambda_arn.split(':')
    if len(parts) == 7:
        return parts[7]
    else:
        return None


def get_lambda_basearn(lambda_arn):
    # the lambda_arn without ALIAS
    parts = lambda_arn.split(':')
    return ':'.join(parts[:7])


class EventSource(object):

    def __init__(self, awsclient, config):
        self._config = deepcopy(config)
        self._awsclient = awsclient
        # currently we do not use the existing enable / disable mechanism
        # but we want to keep the mechanism intact for now
        # for this to work we need to auto-enable all EventSources here
        if 'enabled' not in self._config:
            self._config['enabled'] = True

    @property
    def enabled(self):
        return self._config.get('enabled', False)

    @property
    def arn(self):
        if 'arn' in self._config:
            return self._config['arn']

    @property
    def starting_position(self):
        return self._config.get('starting_position', 'LATEST')

    @property
    def batch_size(self):
        return self._config.get('batch_size', 100)
