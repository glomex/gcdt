## Development of gcdt

### Installation / Usage

All gcdt packages live in a private PyPi repository. See [reposerver](http://reposerver-prod-eu-west-1.infra.glomex.cloud/pypi/) for instructions.

Install the package:

```bash
$ pip install gcdt
```

The repo also has prerelease packages you can use for testing new features or bug fixes:

```bash
$ pip install --pre gcdt
```

Install the development version (after checkout):

```bash
$ pip install -e .
```


### Contributing

If you find any bugs or if you need new features please feel free to issue a pull request with your changes.


### Issues and Feature Requests

Please open a GitHub issue for any bug reports and feature requests.

### Common for all Tools
- All tools imply that your working directory is the directory that contains the artifact you want to work with.
- Furthermore you are responsible for supplying a valid set of AWS credentials. A good tool is [aws-mfa](https://pypi.python.org/pypi/aws-mfa/0.0.5)
- You you need to set an environment variable "ENV" which indicates the account/staging area you want to work with. This parameter tells the tools which config file to use. Basically something like settings_$(ENV).conf is evaluated in the configuration component.
1. All tools use the config_reader module from [glomex-utils](https://github.com/glomex/glomex-utils). This offers some convenient features like looking up values from other CloudFormation stacks, fetching credentials stored in credstash. See the repo documentation for details.


### Installing dev requirements

if you use virtualenv, add the following entry to your $VIRTUAL_ENV/pip.conf file:

```
[global]
timeout = 5
extra-index-url = https://reposerver-prod-eu-west-1.infra.glomex.cloud/pypi/packages
trusted-host = reposerver-prod-eu-west-1.infra.glomex.cloud
```


use pip to install the dev requirements:

```bash
$ pip install -r requirements_dev.txt
```


### gcdt design principles

* write testable code
* tests need to run on all accounts (not just dp account)
* make sure additions and changes have powerful tests
* use pylint to increase your coding style
* we adhere to [Semantic Versioning](http://semver.org/).


### Running Unit-Tests

Use the pytest test-runner to run the gcdt unit tests. A few tests (with '_aws' in the file name) need AWS. Please turn on your VPN and set the AWS_DEFAULT_PROFILE, ENV, and ACCOUNT environment variables. Details here: https://confluence.glomex.com/display/OPSSHARED/Deployment+on+AWS.

You need to install the development version of this package so you can run the tests:

```bash
$ pip install -e .
```

```bash
$ export AWS_DEFAULT_PROFILE=superuser-dp-dev
$ export ENV=DEV
$ export ACCOUNT=dp # => or your team account
```


Note: You need to enter an MFA code to run the tests.

```bash
$ python -m pytest tests/test_kumo*
```

Hint: If you want to see the print outputs use `NOSE_NOCAPTURE=1` as a prefix. 


Please make sure that you do not lower the gcdt test coverage. You can use the following command to make sure:

```bash
$ python -m pytest --cov gcdt tests/test_ramuda*
```

This requires the `coverage` package, which can be installed via pip;
```bash
$ pip install coverage
```

To suppress debug output to more easily find out why (if) the tests break, please run nosetests with the `-vv` option.


### Mock calls to AWS services

For testing gcdt together with boto3 and AWS services we use placebo (a tool by the boto maintainers). The way placebo works is that it is attached to the boto session and used to record and later playback the communication with AWS services (https://github.com/garnaat/placebo).

The recorded placebo json files for gcdt tests are are stored in 'tests/resources/placebo'.

gcdt testing using placebo playback is transparent (if you know how to run gcdt tests nothing changes for you).

To record a test using placebo (first remove old recordings if any):

```bash
$ rm -rf tests/resources/placebo/tests.test_tenkai_aws.test_tenkai_exit_codes/
$ export PLACEBO_MODE=record
$ python -m pytest -vv --cov-report term-missing --cov gcdt tests/test_tenkai_aws.py::test_tenkai_exit_codes
```

To switch off placebo record mode:

```bash
$ export PLACEBO_MODE=playback
```

Please note:

* prerequisite for placebo to work is that all gcdt tools support that the boto session is handed in as parameter (by the test or main). If a module creates its own boto session it breaks gcdt testability.
* in order to avoid merging placebo json files please never record all tests (it would take to long anyway). only record aws tests which are impacted by your change.
* gcdt testing using placebo works well together with aws-mfa.


### documenting gcdt

For the open source version of gcdt we need documentation and we want to publish it on Readthedocs. Consequently some of the toolsing is already set like sphinx, latex, ... We would like to use markdown instead of restructured text so we choose recommonmark.

Detailed information on using [markdown and sphinx](http://blog.readthedocs.com/adding-markdown-support/)


#### Installation of docu tools

```bash
$ pip install -r requirements_docs.txt
```

If you need to create the pdf docu [install pdflatex](https://thetechsolo.wordpress.com/2016/01/28/latex-on-mac-the-easy-way/) (... you also need texlive!).

```bash
$ brew cask install mactex
```

#### build docu

In order to build the html and pdf version of the documentation

```bash
$ make html
$ make latexpdf
```

#### Release docu to Readthedocs

To release the documentation to Readthedocs most of the time there are no additional steps necessary. Just connect your rtfd accoutn to your github repo.


#### Initialize api docu

We used the sphinx-apidoc tool to create the skeleton (80_gcdt_api.rst) for gcdt' api documentation.
```bash
$ sphinx-apidoc -F -o apidocs gcdt
```