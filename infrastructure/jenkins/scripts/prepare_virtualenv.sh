#!/bin/bash -e

# prepare virtualenv

## 
echo "\n## initialize (prepare_virtualenv.sh)"
export PATH=/usr/local/bin:$PATH
virtualenv --clear venv
virtualenv -p /usr/bin/python2.7 --no-site-packages venv

## create pip.conf file
echo "[global]
timeout = 20
extra-index-url = https://reposerver-prod-eu-west-1.infra.glomex.cloud/pypi/packages
trusted-host = reposerver-prod-eu-west-1.infra.glomex.cloud" >> ./venv/pip.conf

##
echo "\n## install requirements"
./venv/bin/pip install -r requirements.txt -r requirements_dev.txt

## 
echo "\n## install gcdt development version"
./venv/bin/pip install -e .
