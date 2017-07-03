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

A little opinionated but pretty common:

* `requirements.txt` tools and packages your service directly depends on
* `requirements_def.txt` tools and packages you need to develop and test your service
* `requirements_gcdt.txt` gcdt and gcdt plugins you use to deploy your service to AWS (see https://github.com/glomex/gcdt#installing-gcdt)
* `requirements_docs.txt` tools you need to write and build your documentation

TODO: document version schema

* add gcdt to your requirements_gcdt.txt
* add the plugins you use to requirements_gcdt.txt


### Installation

#### Setup virtualenv

Using virtualenv is a little bit evolved so some people do not like to use it. There is three things you need to do.

* create a virtualenv ('$ virtualenv venv')
* install the packages you want to use (see below)
* a virtualenv works basically like every other technical device, you need to switch it on before you can use it ('$ source ./venv/bin/activate')


TODO add private repo deps

All gcdt packages live in a private PyPi repository. See [reposerver](http://reposerver-prod-eu-west-1.infra.glomex.cloud/pypi/) for instructions.


#### Activate a virtualenv before use

Again make sure you activate a virtualenv before you can use it:

``` bash
$ source ./venv/bin/activate
```


#### Install your dependencies

``` bash
$ pip install -r requirements.txt -r requirements_dev.txt -r requirements_gcdt.txt
```

If you have additional docs - dependencies for your project you need to install them, too:

``` bash
$ pip install -r requirements_docs.txt
```


#### Deactivate a virtualenv

I do not throw away my lawn mower once I am done but with my terminals I do that. But you can deactivate a virtualenv:

``` bash
$ deactivate
```
