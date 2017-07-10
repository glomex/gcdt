## gcdt command

glomex-cloud-deployment-tools


### Related documents

* [Infrastructure as code](https://martinfowler.com/bliki/InfrastructureAsCode.html)
* [Low-level interface to AWS services](http://botocore.readthedocs.io/en/latest/index.html)

#### Setting the ENV variable

For example if you want to set the environment variable ENV to 'DEV' you can do that as follows:

``` bash
export ENV=DEV
```

### Usage

To see available commands, call gcdt without any arguments:

```bash
$ gcdt
Usage:
        gcdt version
```

### Commands

#### version
If you need help please ask on the gcdt slack channel or open a ticket. For this it is always great if you are able to provide the gcdt version you are using.
A convenient way to find out the version of your gcdt install provides the following command:

```bash
$ gcdt version
Please consider an update to gcdt version: 0.0.74
gcdt version 0.0.33
```

`gcdt version` also provides you with an easy way to check whether a new release of gcdt is available.
