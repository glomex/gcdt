# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging
import json

log = logging.getLogger(__name__)


# note this has currently restricted use to create test artifacts for ramuda wiring

### topic
def create_topic(awsclient, topic):
    client = awsclient.get_client('sns')
    response = client.create_topic(
        Name=topic
    )
    return response['TopicArn']


def delete_topic(awsclient, topic_arn):
    client = awsclient.get_client('sns')
    response = client.delete_topic(
        TopicArn=topic_arn
    )


def send_message(awsclient, topic_arn, message):
    client = awsclient.get_client('sns')
    response = client.publish(
        TargetArn=topic_arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json'
    )
