## Installing gcdt

This chapter covers the gcdt installation. gcdt's behaviour can be customized using plugins. The gcdt plugin mechanism relies on standard Python package mechanisms. In order to get a good experience and get the most out of gcdt you need to know a few things about Python packaging.

This chapter aims to provide you with all the information you need to know on this topic. We also have a screencast in the making related to this topic.

TODO: add the screencast link.


### Related documents

* [Python Package Index](https://pypi.python.org/pypi)


### What you need to know about python package management

TODO

### gcdt package structure

The following diagram gives an overview on the gcdt packages. Please note how we grouped the gcdt packages in the following categories:

* gcdt - the gcdt core (livecycle mechanism, gcdt tools)
* gcdt plugins - packages to customize how you use gcdt
* gcdt generators and tools - scaffolding and tools to make your work even more efficient

![gcdt package structure overview](/_static/images/gcdt-package-structure.png "gcdt package structure overview")

At glomex we have very few (currently one) gcdt packages we do not want to open-source. The glomex-config-reader has very opinionated defaults on how we use gcdt on our AWS infrastructure that is very specific and optimized for our media usecase.

### Maintaining dependencies for your project

It is a very common practice not to install Python packages by hand. Instead dependencies and version are managed in a documented and repeatable way. Basically you add the names and versions of your packages to a text file. Most projects also group their dependencies into `direct` dependencies of the service or application and packages they need to develop, build, test and document.

The grouping is not enforced by packaging but to have a std. within an organization is beneficial especially if your want to reuse CI/CD tools.

The easiest way to install gcdt is via pip and virtualenv.

### Defining which gcdt-plugins to use

gcdt needs at least some gcdt-glugins so you should want to install these together. Add `gcdt` and the plugins you use to *requirements_gcdt.txt*

``` text
gcdt
gcdt-say-hello
gcdt-config-reader
gcdt-lookups
gcdt-bundler
gcdt-slack-integration
gcdt-datadog-integration
gcdt-gen-serverless
```

This is also a best practice to use the `requirements_gcdt.txt` file on your build server.

### Setup virtualenv

We sure every Python dev uses virtualenv on a day to day basis. Using virtualenvs for Python is considered best practise. This is what you need to do:
* create a virtualenv ('$ virtualenv venv')
* install the packages you want to use (see above)
* a virtualenv works basically like every other technical device, you need to switch it on before you can use it ('$ source ./venv/bin/activate')

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

#### Deactivate a virtualenv

I do not throw away my lawn mower once I am done but with my terminals I do that. But you can deactivate a virtualenv:

``` bash
$ deactivate
```

## Updating gcdt
If you need to update `gcdt` just do:
```bash
$ pip install -U -r requirements_gcdt.txt
```
This will update `gcdt` and all `gcdt plugins` specified in *requirements_gcdt.txt*
