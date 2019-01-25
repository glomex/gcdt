#!/bin/bash -e

# Build python package and upload to private PyPi
echo "\n## build and upload (build_package.sh)"
export PATH=/usr/local/bin:$PATH

# build the package and publish to repo server
./venv/bin/python setup.py sdist --dist-dir dist/

# publish the package to repo server
./venv/bin/aws s3 cp --acl bucket-owner-full-control ./dist/ s3://$BUCKET --recursive --exclude '*' --include '*.tar.gz'

# wait for package to be available on PyPi server
# sync is implemented via crontab => 60 seconds
sleep 90
