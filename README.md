[![Documentation](https://readthedocs.org/projects/beedo/badge/?version=latest)](http://gcdt.readthedocs.io/en/latest/)
[![License](http://img.shields.io/badge/license-MIT-yellowgreen.svg)](LICENSE) 
[![GitHub issues](https://img.shields.io/github/issues/glomex/glomex-cloud-deployment-tools.svg?maxAge=2592000)](https://github.com/glomex/glomex-cloud-deployment-tools/issues)

# glomex-cloud-deployment-tools (gcdt)

gcdt is a CLI tool to code and deploy your AWS infrastructure.

The gcdt command line tools have emerged from our experiences at glomex while working extensively with AWS services like Cloudformation, CodeDeploy, AWS Lambda, and API Gateway. gcdt is based on the same technology AWS uses to build AWS-CLI and Boto3 tools. 

In 2017 glomex won the Gartner award "Best Data Management and Infrastructure". Key to our success are the gcdt automation tools we use to successfully complete >100 deployments per day to AWS. Over the course of the last 12 months we built gcdt ourselves using Python.

[![Gartner Award](https://img.youtube.com/vi/DMArRBH2wAk/mqdefault.jpg)](https://www.youtube.com/watch?v=DMArRBH2wAk)

Features include:

* Infrastructure-as-code
* Classic infrastructure (kumo & tenkai)
* Serverless infrastructure (ramuda & yugen)
* Scaffolding
* Powerful plugin mechanism
* Service integration (Slack, Datadog, ...)
* Codify infrastructure best practices
* Multi-Env support (dev, stage, prod, ...)


## Why gcdt?

At glomex we love `continuous-integration-as-code` and `infrastructure-as-code`. This enables us to move fast while providing services of high quality and resilience to our partners.

We added a plugin mechanism to gcdt so we can specialize gcdt to highly optimized and opinionated environments that resonate with our usecases.

We hope gcdt will be helpful to you, too. At glomex we believe that only open source software can become truly great software.


## Useful gcdt information

* [gcdt_userguide](http://gcdt.readthedocs.io/en/latest/)
* [gcdt issues](https://github.com/glomex/gcdt/issues)
* [gcdt project board](https://github.com/glomex/gcdt/projects/1)


## Installing gcdt

The easiest way to install gcdt is via pip and virtualenv.


### Defining which gcdt-plugins to use

gcdt needs at least some gcdt-glugins so you should want to install these together. The easiest way is to put the dependencies into a `requirements_gcdt.txt` file:

``` text
gcdt
gcdt-say-hello
gcdt-config-reader
gcdt-bundler
gcdt-slack-integration
gcdt-datadog-integration
gcdt-gen-serverless
```

This is also a best practice to use the `requirements_gcdt.txt` file on your build server.


### Prepare virtualenv

I am sure every Python dev uses virtualenv on a day to day basis. But we also use gcdt to deploy PHP, Ruby, and NodeJs projects. So I like to cover the basics:

Prepare the venv:

``` bash
$ virtualenv venv
```

Activate the venv for use:

``` bash
$ source ./venv/bin/activate
```


### Installing all dev dependencies in one go 

Install the dependencies into venv:

``` bash
$ pip install -r requirements_gcdt.txt
```

Now you can start using gcdt:

``` bash
$ gcdt version
```

BTW, `gcdt version` shows you all the versions of gcdt and installed plugins. So you can use this to quickly check which plugins are installed. 


## Contributing

At glomex we welcome feedback, bug reports, and pull requests!

For pull requests, please stick to the following guidelines:

* Add tests for any new features and bug fixes. Ideally, each PR should increase the test coverage.
* Follow the existing code style (e.g., indents). UseA PEP8 code linting.
* Put a reasonable amount of comments into the code.
* Separate unrelated changes into multiple pull requests.


## License

Copyright (c) 2017 glomex and others.
gcdt is released under the MIT License (see LICENSE).
