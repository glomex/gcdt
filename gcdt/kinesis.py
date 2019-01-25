# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging

log = logging.getLogger(__name__)


# note this has currently restricted use to create test artifacts for ramuda wiring

### stream
def create_stream(awsclient, stream_name, shard_count=1):
    client = awsclient.get_client('kinesis')
    response = client.create_stream(
        StreamName=stream_name,
        ShardCount=shard_count
    )


def wait_for_stream_exists(awsclient, stream_name):
    # helper to wait for stream to become operational
    client = awsclient.get_client('kinesis')
    waiter = client.get_waiter('stream_exists')

    waiter.wait(StreamName=stream_name)


def describe_stream(awsclient, stream_name):
    client = awsclient.get_client('kinesis')
    response = client.describe_stream(
        StreamName=stream_name
    )
    return response['StreamDescription']


def delete_stream(awsclient, stream_name):
    client = awsclient.get_client('kinesis')
    response = client.delete_stream(
        StreamName=stream_name
    )
