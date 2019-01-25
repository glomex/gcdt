# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import logging
from s3transfer import S3Transfer
from botocore.client import ClientError

log = logging.getLogger(__name__)


### bucket
def prepare_artifacts_bucket(awsclient, bucket):
    """Prepare the bucket if it does not exist.

    :param bucket:
    """
    if not bucket_exists(awsclient, bucket):
        create_versioned_bucket(awsclient, bucket)


def bucket_exists(awsclient, bucket):
    client_s3 = awsclient.get_client('s3')
    try:
        client_s3.head_bucket(Bucket=bucket)
        return True
    except ClientError:
        return False


def create_versioned_bucket(awsclient, bucket):
    client_s3 = awsclient.get_client('s3')
    client_s3.create_bucket(
        Bucket=bucket,
        CreateBucketConfiguration={
            'LocationConstraint': 'eu-west-1'
        }
    )
    client_s3.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={
            'Status': 'Enabled'
        }
    )


def create_bucket(awsclient, bucket):
    client = awsclient.get_client('s3')
    client.create_bucket(
        Bucket=bucket,
        CreateBucketConfiguration={
            'LocationConstraint': 'eu-west-1'
        }
    )


def delete_bucket(awsclient, bucket):
    # this works up to 1000 keys
    log.debug('deleting bucket %s' % bucket)
    if bucket.startswith('unittest-'):
        client_s3 = awsclient.get_client('s3')
        # delete all objects first
        log.debug('deleting keys')
        objects = client_s3.list_objects_v2(Bucket=bucket)
        if objects['KeyCount'] > 0:
            delete = {'Objects': [{'Key': k['Key']} for k in objects['Contents']]}
            client_s3.delete_objects(Bucket=bucket, Delete=delete)

        log.debug('deleting bucket')
        # now we can delete the bucket
        client_s3.delete_bucket(Bucket=bucket)


### keys
def upload_file_to_s3(awsclient, bucket, key, filename):
    """Upload a file to AWS S3 bucket.

    :param awsclient:
    :param bucket:
    :param key:
    :param filename:
    :return:
    """
    client_s3 = awsclient.get_client('s3')
    transfer = S3Transfer(client_s3)
    # Upload /tmp/myfile to s3://bucket/key and print upload progress.
    transfer.upload_file(filename, bucket, key)
    response = client_s3.head_object(Bucket=bucket, Key=key)
    etag = response.get('ETag')
    version_id = response.get('VersionId', None)
    return etag, version_id


def remove_file_from_s3(awsclient, bucket, key):
    """Remove a file from an AWS S3 bucket.

    :param awsclient:
    :param bucket:
    :param key:
    :return:
    """
    client_s3 = awsclient.get_client('s3')
    response = client_s3.delete_object(Bucket=bucket, Key=key)


def ls(awsclient, bucket, prefix=None):
    """List bucket contents

    :param awsclient:
    :param bucket:
    :param prefix:
    :return:
    """
    # this works until 1000 keys!
    params = {'Bucket': bucket}
    if prefix:
        params['Prefix'] = prefix
    client_s3 = awsclient.get_client('s3')
    objects = client_s3.list_objects_v2(**params)
    if objects['KeyCount'] > 0:
        keys = [k['Key'] for k in objects['Contents']]
        return keys
