#!/bin/bash -e

# Merge develop into master and bump version and release to PyPi

# Setup virtualenv in temp folder
TEMP_DIR=`mktemp -d` && cd ${TEMP_DIR}
virtualenv -p /usr/bin/python2.7 --no-site-packages venv
./venv/bin/pip install --upgrade pip

# create pip.conf file
echo "[global]
timeout = 20
extra-index-url = https://reposerver-prod-eu-west-1.infra.glomex.cloud/pypi/packages
trusted-host = reposerver-prod-eu-west-1.infra.glomex.cloud" >> ./venv/pip.conf

source ./venv/bin/activate

########
# Debug

echo "-INPUT---------------"
echo "AWS_DEFAULT_REGION   : ${AWS_DEFAULT_REGION}"
echo "BRANCH          	   : ${PYPI_REPO}"
echo "WORKSPACE            : ${WORKSPACE}"
echo "TEMP_DIR             : ${TEMP_DIR}"
echo "ENV                  : ${ENV}"
echo "PACKAGE_NAME         : ${PACKAGE_NAME}"
echo "ARTIFACT_BUCKET      : ${ARTIFACT_BUCKET}"
echo "PYTHONUNBUFFERED     : ${PYTHONUNBUFFERED}"
echo "BUCKET               : ${BUCKET}"
echo "-INPUT END-----------"


########
# merge develop branch into master
cd $WORKSPACE
git checkout develop
git checkout master
git merge develop


########
# Install dependencies
pip install -r requirements.txt -r requirements_dev.txt


########
# Release
echo "bumping version to release"
bumpversion --commit --tag release
git checkout develop
git merge master

python setup.py sdist --dist-dir dist/
ls -la dist/

# install the awscli
pip install awscli --ignore-installed six

# publish to PyPi server
aws s3 cp --acl bucket-owner-full-control ./dist/ s3://$BUCKET --recursive --exclude '*' --include '*.tar.gz'

# now we need to bump patch level
echo "bumping patch level"
bumpversion --commit patch


########
#clean up
rm -rf ${TEMP_DIR}