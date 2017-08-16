## gcdt command

glomex-cloud-deployment-tools


### Related documents

* [Infrastructure as code](https://martinfowler.com/bliki/InfrastructureAsCode.html)
* [Low-level interface to AWS services](http://botocore.readthedocs.io/en/latest/index.html)

#### Setting the ENV variable

You you need to set an environment variable "ENV" which indicates the account/staging area you want to work with. This parameter tells the tools which config file to use. For example if you want to set the environment variable ENV to 'DEV' you can do that as follows:

``` bash
export ENV=DEV
```

### Usage

To see available commands, call gcdt without any arguments:

```bash
$ gcdt
Usage:
        gcdt config
        gcdt version
```

### Commands

#### config
This command is intended to provide tooling support for maintaining configuration.

The `config` command does the following:

* read configuration defaults
* read the config from file ('gcdt_<env>.json')
* run the lookups
* format and output the config to the console

#### version
If you need help please ask on the gcdt slack channel or open a ticket. For this it is always great if you are able to provide information about the gcdt version you are using.
A convenient way to find out the version of your gcdt install provides the following command:

```bash
$ gcdt version
WARNING: Please consider an update to gcdt version: 0.1.433
gcdt version 0.1.432
gcdt plugins:
 * gcdt-config-reader version 0.0.11
 * gcdt-bundler version 0.0.27
 * gcdt-slack-integration version 0.0.11
 * gcdt-datadog-integration version 0.0.15
 * gcdt-lookups version 0.0.12
```

`gcdt version` also provides you with an easy way to check whether a new release of gcdt is available.
