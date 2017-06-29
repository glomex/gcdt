## gcdt command

glomex-cloud-deployment-tools


### Related documents

* [Infrastructure as code](https://martinfowler.com/bliki/InfrastructureAsCode.html)
* [Low-level interface to AWS services](http://botocore.readthedocs.io/en/latest/index.html)

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


### Installation

We at glomex SRE want to make the installation of gcdt on OS X as easy as possible. With the new installer the gcdt installation is just a single step.

The only prerequiste we have for the gcdt installation is that you have a current python2.7 version installed (>= 2.7.9) on your Mac.

I installed my python with the following command:

```bash
$ brew install python
```


### Update gcdt to a newer version

New gcdt versions usually are released once per week. You should try to stay current so you are able to benefit from new features and bug-fixes. To check if a new gcdt version is available use `gcdt version` (see above).

```bash
$ ~/.venv-gcdt/bin/pip install gcdt
```

Note: this only works if you have installed gcdt using its installer (see above).
