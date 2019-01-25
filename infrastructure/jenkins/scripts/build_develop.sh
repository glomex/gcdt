#!/bin/bash -e
#
# Dependency compile & version bumping (dev level) on develop branch

########
# Preparation
export PATH=/usr/local/bin:$PATH

# Setup virtualenv in temp folder
TEMP_DIR=`mktemp -d` && cd ${TEMP_DIR}
virtualenv -p /usr/bin/python2.7 --no-site-packages venv
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
# Install dependencies
cd $WORKSPACE
pip install -r requirements.txt -r requirements_dev.txt


########
# Version
echo "bumping dev level in develop"
bumpversion --commit patch


########
# Release
# python setup.py sdist --dist-dir dist/
echo "[server-login]
username:glomex
password:$(credstash -r eu-west-1 get jenkins.pypi.password)" > ~/.pypirc

# publish to repo server
python setup.py sdist upload


########
#clean up
rm -rf ${TEMP_DIR}
