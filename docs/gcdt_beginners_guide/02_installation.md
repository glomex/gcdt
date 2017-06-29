# Getting Started Guide
Welcome to the beginners guide of `gcdt`. In this guide we will cover what `gcdt` is and how to use it to
create beautiful infrastructure as code (IaC) with `kumo`, use it to deploying and configuring you AWS Lambda with `ramuda`,
deploy your application with Codedeploy scripts and `tenkai`, and do all of this things for different Environment (dev, stage, prod)
## Infrastructure as code
Infrastructure as Code (IAC) is a type of IT infrastructure that operations teams can automatically manage and provision through code, rather than using a manual process. Defining your infrastructure as code you will solve a lot of problems because code is:
- portable
- reusable
- shareable
- testable.
## What is gcdt?
gcdt is a CLI tool to code and deploy your AWS infrastructure.
The gcdt command line tools have emerged from our experiences at glomex while working extensively with AWS services like
Cloudformation, CodeDeploy, AWS Lambda, and API Gateway. gcdt is based on the same technology AWS uses to build AWS-CLI
and Boto3 tools.
## Installation
### Install Python
First of all you need to install Python. Python should be 2.7.9 or higher
#### Linux/Ubuntu
```bash
$ sudo apt-get update
$ sudo apt-get install python
```
#### Linux/CentOS
```bash
$ sudo yum update
$ sudo yum install python
```
#### MacOS
```bash
$ brew install python
```
### Install pip and virtualenv
#### Linux/Ubuntu
```bash
$ sudo apt-get -y install python-pip
$ sudo pip install pip --upgrade # to have the latest version of pip
$ sudo pip install virtualenv
```
#### Linux/CentOS
```bash
$ sudo yum install epel-release
$ sudo yum install python-pip
$ sudo pip install pip --upgrade # to have the latest version of pip
$ sudo pip install virtualenv
```
#### MacOS
```bash
$ sudo easy install pip
$ sudo pip install pip --upgrade # to have the latest version of pip
$ sudo pip install virtualenv
```
### Install gcdt and gcdt plugins
#### Install gcdt
First of all you need to create virtualenv and activate it. It's pretty easy.
```bash
$ virtualenv venv
$ source ./venv/bin/activate
$ pip install -r requirements.txt -r requirements_dev.txt
```
To check that everything is good and `gcdt` installed just do:
```bash
$ gcdt version
  gcdt version 0.1.403
  gcdt plugins:
```
#### Install gcdt plugins
As you see above there is no plugins after installation. Let's install some useful one.
Plugins is a powerful tool to add features to `gcdt` without having to directly modify the `gcdt` core.
Here is the plugins name and short description.

| Plugin name  | Description  |
|---|---|
| gcdt-datadog-integration  | send deployment metrics and events to datadog  |
|  gcdt-config-reader |  read configuration files in json, python, or yaml format |
| glomex-config-reader  |  read hocon configuration files |
| gcdt-lookup | lookup information related to your AWS account |
| gcdt-slack-integration | send deployment status information to slack |
| glomex-checks | useful checks of your configs, vpn connection, virtualenv version, etc  |

Let's install all base plugins what we need to start using gcdt:
```bash
$ pip install gcdt-config-reader gcdt-lookup
```
