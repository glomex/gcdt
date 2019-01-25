# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

from gcdt.event_source import base


def test_get_lambda_name():
    lambda_arn = 'arn:aws:lambda:eu-west-1:420189626185:function:jenkins_test_gnicdo'
    assert base.get_lambda_name(lambda_arn) == 'jenkins_test_gnicdo'


def test_get_lambda_name_alias():
    lambda_arn = 'arn:aws:lambda:eu-west-1:420189626185:function:jenkins_test_gnicdo:ACTIVE'
    assert base.get_lambda_name(lambda_arn) == 'jenkins_test_gnicdo'
