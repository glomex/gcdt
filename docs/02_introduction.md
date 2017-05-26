## Introduction

This userguide aims to make it easy for you to get started using the gcdt tools in your projects. gcdt helps you to code your infrastructure on AWS and put it under version control as infrastructure-as-code together with the implementation of your service. In this way you can fully automate your infrastructure and your service deployments.

gcdt provides tools for traditional compute services and also managed serverless computing services. gcdt was implemented internally at glomex.

[glomex](http://www.glomex.com/) – The Global Media Exchange – is a provider of a global, open marketplace for premium video content as well as a technical service provider for the entire value chain of online video marketing.

gcdt and userguide are released under [BSD-3 License](http://github.com/glomex/glomex-cloud-deployment-tools/LICENSE.md).

The gcdt userguide starts with this introduction, then provides an overview on gcdt like a guided tour on how gcdt is structured and what it offers to you. The following parts each covers one gcdt tool. The remaining parts go into more technical topics like developing gcdt or using it as library to build your own tools based on gcdt.

This user guide assumes that you know the AWS services you want to automate so we do not cover AWS services in great detail and instead point to relevant documentation. But even if you are starting out on AWS, gcdt will help you to quickly leave the AWS webconsole behind and to move towards infrastructure-as-code.


### gcdt software version

This guide covers gcdt version '0.1.68'.


### Related documents

This section aims to provide to you a list of related documents that will be useful to gain a detailed understanding about what the gcdt tool suite does. With this background you will be able to tap into the full potential of the gcdt tools.  

* [Infrastructure as code](https://martinfowler.com/bliki/InfrastructureAsCode.html)
* [AWS IAM service](https://aws.amazon.com/iam/)
* [AWS S3 service](https://aws.amazon.com/s3/)
* [AWS CloudFormation service](https://aws.amazon.com/cloudformation/)
* [AWS Codedeploy service](https://aws.amazon.com/codedeploy/)
* [AWS Lambda service](https://aws.amazon.com/lambda/)
* [AWS API Gateway service](https://aws.amazon.com/api-gateway/)
* [Low-level interface to AWS services](http://botocore.readthedocs.io/en/latest/index.html)


### Problem reporting instructions

Please use Github issues to report gcdt issues: [gcdt issues](https://github.com/glomex/glomex-cloud-deployment-tools/issues). To check on the progress check out the gcdt project board: [gcdt project board](https://github.com/glomex/glomex-cloud-deployment-tools/projects/1)

glomex employess can get immediate user support via [gcdt slack channel](https://glomex-team.slack.com/messages/gcdt/) or just stop by the glomex SRE lab in Munich, Landsberger Straße 110 
 at P-02-041.
