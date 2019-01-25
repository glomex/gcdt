[![Documentation](https://readthedocs.org/projects/beedo/badge/?version=latest)](http://gcdt.readthedocs.io/en/latest/)
[![License](http://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/glomex/glomex-cloud-deployment-tools.svg?maxAge=2592000)](https://github.com/glomex/glomex-cloud-deployment-tools/issues)

# glomex-cloud-deployment-tools (gcdt)

gcdt CLI tools make it easy for you to code, automate, and deploy your AWS infrastructure.

The gcdt command line tools have emerged from our experiences at glomex while working extensively with AWS services like Cloudformation, CodeDeploy, AWS Lambda, and API Gateway. gcdt is based on the same technology AWS uses to build AWS-CLI and Boto3 tools.

In 2017 glomex won the Gartner award "Best Data Management and Infrastructure". Key to our success are the gcdt CLI tools we use to successfully complete >3000 deployments per month to AWS. Over the course of the last 18 months we built gcdt ourselves using Python.

[![Gartner Award](https://img.youtube.com/vi/DMArRBH2wAk/mqdefault.jpg)](https://www.youtube.com/watch?v=DMArRBH2wAk)

Features include:

* Infrastructure-as-code
* Cloud infrastructure (kumo & tenkai)
* Serverless infrastructure (ramuda & yugen)
* Scaffolding
* Powerful plugin mechanism
* Service integration (Slack, Datadog, ...)
* Codify infrastructure best practices
* Multi-Env support (dev, stage, prod, ...)

At glomex we love `continuous-integration-as-code` and `infrastructure-as-code`. This enables us to move fast while providing services of high quality and resilience to our partners.

We added a plugin mechanism to gcdt so we can specialize gcdt to highly optimized and opinionated environments that resonate with our usecases.

We hope gcdt will be helpful to you, too. At glomex we believe that only open source software can become truly great software.


## Why gcdt?

You can do everything gcdt does by using the AWS Management Console so why use gcdt? Basically, because using GUI interfaces to drive your production environment is a really bad idea. You can't really automate GUI interfaces, you can't debug GUI interfaces, and you can't easily share techniques and best practices with a GUI.

The goal of gcdt is to put everything about your AWS infrastructure into files on a filesystem which can be easily versioned and shared. Once your files are in git, people on your team can create pull requests to merge new changes in and those pull requests can be reviewed, commented on, and eventually approved. This is a tried and proven approach that has worked for more traditional deployment methodologies and will also work for your infrastructure on AWS.


## Useful gcdt information

* [gcdt_userguide](http://gcdt.readthedocs.io/en/latest/)
* [gcdt issues](https://github.com/glomex/gcdt/issues)
* [gcdt project board](https://github.com/glomex/gcdt/projects/1)


## Installation

Follow the [instructions](http://gcdt.readthedocs.io/en/latest/07_installation.html) to install `gcdt`


## Contributing

Here you can find the full guide for [contributing](http://gcdt.readthedocs.io/en/latest/70_development.html)

At glomex we welcome feedback, bug reports, and pull requests!

For pull requests, please stick to the following guidelines:

* Add tests for any new features and bug fixes. Ideally, each PR should increase the test coverage.
* Follow the existing code style. Use PEP8 code linting.
* Put a reasonable amount of comments into the code.
* Separate unrelated changes into multiple pull requests.


## License

Copyright (c) 2017 glomex and others.
gcdt is released under the MIT License (see LICENSE).
