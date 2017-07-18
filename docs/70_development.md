## Development of gcdt

### Contributing

If you find any bugs or if you need new features please feel free to issue a pull request with your changes.

### Issues and Feature Requests

Please open a GitHub issue for any bug reports and feature requests.

### Common for all Tools
- All tools imply that your working directory is the directory that contains the artifact you want to work with.
- Furthermore you are responsible for supplying a valid set of AWS credentials. A good tool is [aws-mfa](https://pypi.python.org/pypi/aws-mfa/0.0.5)
- You you need to set an environment variable "ENV" which indicates the account/staging area you want to work with. This parameter tells the tools which config file to use. Basically something like gcdt_$(ENV).json is evaluated in the configuration component.

### Installing the development version locally

To install your local development version (after checkout):

```bash
$ pip install -e .
```

use pip to install the dev requirements:

```bash
$ pip install -r requirements_dev.txt
```

### Running Unit-Tests

Use the pytest test-runner to run the gcdt unit tests. A few tests (with '_aws' in the file name) need AWS. Please turn on your VPN and set the `AWS_DEFAULT_PROFILE`, `ENV`, and `ACCOUNT` environment variables. Details here: https://confluence.glomex.com/display/OPSSHARED/Deployment+on+AWS.

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

Please make sure that you do not lower the gcdt test coverage. You can use the following command to make sure:

```bash
$ python -m pytest --cov gcdt tests/test_ramuda*
```

This requires the `coverage` package (included in the `requirements_dev.txt` file):

```bash
$ pip install -r requirements_dev.txt
```

### Mock calls to AWS services

For testing gcdt together with botocore and AWS services we use placebo_awsclient (a tool based on the boto maintainers placebo project). The way placebo_awsclient works is that it is attached to the botocore session and used to record and later playback the communication with AWS services.

The recorded json files for gcdt tests are stored in 'tests/resources/placebo_awsclient'.

gcdt testing using placebo playback is transparent (if you know how to run gcdt tests nothing changes for you).

To record a test using placebo **(first remove old recordings if any)**:

```bash
$ rm -rf tests/resources/placebo_awsclient/tests.test_tenkai_aws.test_tenkai_exit_codes/
$ export PLACEBO_MODE=record
$ python -m pytest -vv --cov-report term-missing --cov gcdt tests/test_tenkai_aws.py::test_tenkai_exit_codes
```

To switch off placebo record mode and use playback mode:

```bash
$ export PLACEBO_MODE=playback
```

To run the tests against AWS services (without recording) use `normal` mode:

```bash
$ export PLACEBO_MODE=normal
```

**Please note:**

* prerequisite for placebo to work is that all gcdt tools support that the awsclient is handed in as parameter (by the test or main). If a module creates its own botocore session it breaks gcdt testability.
* in order to avoid merging placebo json files please **never record all tests (it would take to long anyway)**. only record aws tests which are impacted by your change.
* gcdt testing using placebo works well together with aws-mfa.
* if you record the tests twice the json files probably get messed up.
  Please do not do this.
* Please commit the placebo files in a separate commit. This makes reviewing of pull requests easier.

### documenting gcdt

For gcdt we need documentation and we publish it on Readthedocs. Consequently the tooling is already set like sphinx, latex, ... We would like to use markdown instead of restructured text so we choose recommonmark.

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

To release the documentation to Readthedocs most of the time there are no additional steps necessary. Just connect your rtfd account to your github repo.

#### Initialize api docu

We used the sphinx-apidoc tool to create the skeleton (80_gcdt_api.rst) for gcdt' api documentation.
```bash
$ sphinx-apidoc -F -o apidocs gcdt
```

### gcdt design

#### Design Goals

* support development teams with tools and templates
* ease, simplify, and master infrastructure-as-code

#### Design Principles

* write testable code
* tests need to run on all accounts (not just dp account)
* make sure additions and changes have powerful tests
* use pylint to increase your coding style
* we adhere to [Semantic Versioning](http://semver.org/).

#### Design Decisions

In this section we document important design decisions we made over time while maintaining gcdt.

##### Use botocore over boto3

With botocore and boto3 AWS provides two different programmatic interfaces to automate interaction with AWS services.

One of the most noticeable differences between botocore and boto3
is that the client objects:

1) require parameters to be provided as ``**kwargs``
2) require the arguments typically be provided as ``CamelCased`` values.

For example::

    ddb = session.create_client('dynamodb')
    ddb.describe_table(TableName='mytable')

In boto3, the equivalent code would be::

    layer1.describe_table(table_name='mytable')

There are several reasons why this was changed in botocore.

The first reason was because we wanted to have the same casing for
inputs as well as outputs.  In both boto3 and botocore, the response
for the ``describe_table`` calls is::

    {'Table': {'CreationDateTime': 1393007077.387,
                'ItemCount': 0,
                'KeySchema': {'HashKeyElement': {'AttributeName': 'foo',
                                                 'AttributeType': 'S'}},
                'ProvisionedThroughput': {'ReadCapacityUnits': 5,
                                          'WriteCapacityUnits': 5},
                'TableName': 'testtable',
                'TableStatus': 'ACTIVE'}}

Notice that the response is ``CamelCased``.  This makes it more difficult
to round trip results.  In many cases you want to get the result of
a ``describe*`` call and use that value as input through a corresponding
``update*`` call.  If the input arguments require ``snake_casing`` but
the response data is ``CamelCased`` then you will need to manually convert
all the response elements back to ``snake_case`` in order to properly
round trip.

This makes the case for having consistent casing for both input and
output.  Why not use ``snake_casing`` for input as well as output?

We choose to use ``CamelCasing`` because this is the casing used by
AWS services.  As a result, we don't have to do any translation from
``CamelCasing`` to ``snake_casing``.  We can use the response values
exactly as they are returned from AWS services.

This also means that if you are reading the AWS API documentation
for services, the names and casing referenced there will match
what you would provide to botocore.  For example, here's the
corresponding API documentation for
`dynamodb.describe_table
<http://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_DescribeTable.html>`__.

#### Use pytest over nose

For many years py.test and nose coexisted as Python unit test frameworks in addition to std. Python unittest. Nose was developed by Mozilla and was popular for quite some time. In 2015 Mozilla switched from nose to pytest.

http://mathieu.agopian.info/presentations/2015_06_djangocon_europe/

There are many arguments in favour of pytest. For us the most important is pytest fixtures which provides us with a reliable and reusable mechanism to prepare and cleanup resources used during testing.


#### Capturing of log output during test

In our tests we use a `logcapture` fixture from gcdt_testtools.helpers to capture log output. The fixture use the textfixtures package under the hood.

use it like this:
``` python
logcapture.check(
    ('root', 'INFO', 'a message'),
    ('root', 'ERROR', 'another error'),
)
```

or:
``` python
records = list(logcapture.actual())
assert records[0][2] == 'a message'
```

details here: http://testfixtures.readthedocs.io/en/latest/logging.html


#### Use Sphinx, Readthedocs, and Markdown for documentation

Many, many documentation tools populate this space since it is so easy to come up with something. However for Open Source projects Readthedocs is the dominant platform to host the documentation.

The Sphinx is the Python std. docu tool. In combination with markdown tools set is a very convenient way to create Readthedocs conform documentation.

#### Keep a changelog

We where already keeping a changelog which "almost" followed the guide. In June 2017 we decided to make the format more explicit.

The gcdt changelog format is defined here: http://keepachangelog.com/en/1.0.0/

#### Use docopt to build the command line interface

There is a never-ending discussion going about pros and cons of CLI tools for Python. Some of these tools are contained in the Python std. library, some are independent open source library additions. At the moment the most popular tools are Optparse, Argparse, Click, and Docopt

https://www.youtube.com/watch?v=pXhcPJK5cMc

We decided to use docopt for out command line interface because it is simple and very flexible. In addition we developed a `dispatch mechanism` to ease the docopt usage and to make the gcdt CLI commands testable.

#### Using Maya: Datetimes for Humans

We had some issues in the past using datetimes correctly across different timezones and locales. glomex SRE team took an initiative to improve the situation and we. We looked into pytz and maya. Maya had a convincing offering and is maintained by Kenneth Reitz so we decided to use it for datetime handling within gcdt.

#### Plugin mechanism

gcdt uses entry points similar to [pluggy](https://github.com/pytest-dev/pluggy) to find installed plugins

For communication with the plugin we use [Blinker signals](https://pythonhosted.org/blinker/). This helps us to decouple the gcdt code base from plugin code and vice-versa. Blinker is of cause only one way to do that. Blinker is fast, simple, well documented, etc. so there are some popular frameworks using it (Flask, Pelican, ...).
