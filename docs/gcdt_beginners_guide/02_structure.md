# Getting Started Guide
Welcome to the beginners guide of `gcdt`. In this guide we will cover what `gcdt` is and how to use it to
create beautiful infrastructure as code (IaC) with `kumo`, use it to deploying and configuring you AWS Lambda with `ramuda`,
deploy your application with Codedeploy scripts and `tenkai`, and do all of this things for different Environment (dev, stage, prod)
## What is gcdt?
gcdt is a CLI tool to code and deploy your AWS infrastructure.
The gcdt command line tools have emerged from our experiences at glomex while working extensively with AWS services like
Cloudformation, CodeDeploy, AWS Lambda, and API Gateway. gcdt is based on the same technology AWS uses to build AWS-CLI
and Boto3 tools.
## Installation
### Install Python
First of all you need to install Python
#### Linux/Ubuntu
```bash
sudo apt-get update
sudo apt-get install python
```
#### Linux/CentOS
```bash
sudo yum update
sudo yum install python
```
#### MacOS
```bash
brew install python
```
### Install pip and virtualenv
#### Linux/Ubuntu
```bash
sudo apt-get -y install python-pip
sudo pip install pip --upgrade # to have the latest version of pip
sudo pip install virtualenv
```
#### Linux/CentOS
```bash
sudo yum install epel-release
sudo yum install python-pip
sudo pip install pip --upgrade # to have the latest version of pip
sudo pip install virtualenv
```
#### MacOS
```bash
sudo easy install pip
sudo pip install pip --upgrade # to have the latest version of pip
sudo pip install virtualenv
```
### Install gcdt and gcdt plugins

## Kumo
### Good to know
Links to AWS Cloudformation docs and troposphere.
### Create your first stack with kumo
Provide examples from gcdt-sample-stack. Explain how to create setting for different ENV
### Deploy stack to AWS
Create screencast of working kumo deploy
### Useful kumo command

## Tenkai
### Good to know
Links to AWS Codedeploy docs
### Create Codedeploy bundle
Provide examples from gcdt-sample-stack.
### Deploy into AWS
Create screencast of working tenkai deploy
### Useful tenkai command

## Ramuda
### Good to know
Links to AWS Lambda docs
### Create simple AWS Lambda
Provide examples from gcdt-sample-stack.
### Deploy AWS Lambda with Ramuda
Create screencast of working ramuda deploy
### Useful ramuda command

## Yugen
### Good to know
Links to AWS API Gateway docs
### Create simple AWS API Gateway
Provide examples from gcdt-sample-stack.
### Deploy AWS API Gateway with yugen
Create screencast of working yugen deploy
### Useful yugen command
