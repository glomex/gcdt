#!/bin/bash -e

# execute lifecycle for gcdt tools on the infra-dev stack via gcdt CLI
# this script is supposed to run within the Jenkins gcdt pull request builder
echo "\n## E2E lifecycle (gcdt_lifecycle.sh)"


# create temp folder
cwd=$(pwd)
folder=`mktemp -d -t gcdt_unittest_XXXXXXXX`
echo "using temp folder: $folder"
cd $folder

export PATH=/usr/local/bin:$PATH


# checkout sample app
# this needs "Credentials Binding Plugin" to work (v)
# note: GIT_CREDENTIALS (conjoined) comes as username:password
username=${GIT_CREDENTIALS%:*}
password=${GIT_CREDENTIALS#*:}
git clone https://${username}:${password}@github.com/glomex/gcdt-sample-stack.git

# prepare virtualenvs
virtualenv --clear venv
virtualenv -p /usr/bin/python2.7 --no-site-packages venv


# create pip.conf file so we get PR version from reposerver
echo "[global]
timeout = 20
extra-index-url = https://reposerver-prod-eu-west-1.infra.glomex.cloud/pypi/packages
trusted-host = reposerver-prod-eu-west-1.infra.glomex.cloud" >> ./venv/pip.conf


# install the gcdt PR package
source ./venv/bin/activate
pip install gcdt==PR$ghprbPullId


# install the sample stacks
cd gcdt-sample-stack
export WORKSPACE=$(pwd)
export BUILD_TAG=GCDT_PR$ghprbPullId
export ENV=DEV


# install gcdt plugins and dependencies
pip install -r requirements_gcdt.txt


#######
## kumo
./infrastructure/jenkins/jenkins_cloudformation.sh


#######
## tenkai
./infrastructure/jenkins/jenkins_codedeploy.sh

## check if the application works
sleep 180
curl --fail http://autotest:tsetotua@supercars-eu-west-1.dev.infra.glomex.cloud/health_check

## stop the stack
cd ./infrastructure
kumo stop

## start the stack
cd ./infrastructure
kumo start

## check if the application works (after health checks are green)
sleep 20
curl --fail http://autotest:tsetotua@supercars-eu-west-1.dev.infra.glomex.cloud/health_check

## cleanup the stack
cd ./infrastructure
kumo delete -f


#######
# ramuda lifecycle
cd $WORKSPACE/sample_lambda
ramuda bundle
ramuda deploy
ramuda ping jenkins-gcdt-lifecycle-for-ramuda
ramuda metrics jenkins-gcdt-lifecycle-for-ramuda
ramuda delete -f jenkins-gcdt-lifecycle-for-ramuda


#######
# yugen lifecycle
cd $WORKSPACE/sample_api

echo "$ yugen apikey-create jenkins-yugen-testkey"
yugen apikey-create jenkins-yugen-testkey | tee apikey.txt
key=$(cat apikey.txt | grep -oP "api key '\K(.+)(?=' to your api.conf)")

echo "adding key to conf file: $key"
sed -i -e "s/apiKey = \"\w*\"/apiKey = \"${key}\"/g" api_dev.conf

echo "$ yugen apikey-list"
yugen apikey-list

echo "$ yugen deploy"
yugen deploy

echo "$ yugen list"
yugen list

echo "$ yugen export"
yugen export

echo "$ yugen delete -f"
yugen delete -f

echo "$ yugen apikey-delete"
yugen apikey-delete


#######
# python3.6 lifecycle steps
cd $folder
virtualenv --clear venv3
virtualenv -p /usr/local/bin/python3.6 --no-site-packages venv3

# create pip.conf file so we get PR version from reposerver
echo "[global]
timeout = 20
extra-index-url = https://reposerver-prod-eu-west-1.infra.glomex.cloud/pypi/packages
trusted-host = reposerver-prod-eu-west-1.infra.glomex.cloud" >> ./venv3/pip.conf

# install the gcdt PR package
source ./venv3/bin/activate
pip install gcdt==PR$ghprbPullId

# install the sample stacks
cd gcdt-sample-stack
pip install -r requirements_gcdt.txt


#######
# ramuda lifecycle
cd $WORKSPACE/sample_lambda
ramuda bundle
ramuda deploy
ramuda ping jenkins-gcdt-lifecycle-for-ramuda
ramuda metrics jenkins-gcdt-lifecycle-for-ramuda
ramuda delete -f jenkins-gcdt-lifecycle-for-ramuda


#######
# cleanup the temp folder
cd $cwd
if [ "$folder" = "" ]; then
    echo '$folder var is empty - bailing out!'
    exit
fi
echo "removing temp folder..."
rm -rf $folder
