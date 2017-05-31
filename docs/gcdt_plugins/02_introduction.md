## Introduction

Beginning with version 0.0.77 gcdt supports plugins. Plugins are a way to add features to gcdt without having to directly modify the gcdt core.

This gcdt plugin userguide aims to make it easy for you to get started using plugins in your projects. gcdt-plugins help you customize the gcdt tools towards your specific project needs.

gcdt plugins are available for many different areas from reading your specific configuration format, to looking up credentials from your secret-store. gcdt plugins were implemented internally at glomex.

[glomex](http://www.glomex.com/) – The Global Media Exchange – is a provider of a global, open marketplace for premium video content as well as a technical service provider for the entire value chain of online video marketing.

gcdt plugins and userguide are released under [MIT License](http://github.com/glomex/gcdt/LICENSE).

The gcdt plugins userguide starts with this introduction, then provides an overview on how to use and configure gcdt plugins in general. The following parts each cover one gcdt plugin.

This user guide assumes that you know gcdt and the AWS services you want to automate so we do not cover AWS services in great detail and instead point to relevant documentation. But even if you are starting out on AWS, gcdt will help you to quickly leave the AWS webconsole behind and to move towards infrastructure-as-code.


### Related documents

This section aims to provide to you a list of related documents that will be useful to gain a detailed understanding about what the gcdt tool suite does. With this background you will be able to tap into the full potential of the gcdt tools.  

* [gcdt (glomex-cloud-deployment-tools)](https://github.com/glomex/gcdt)
* [blinker signals](https://pythonhosted.org/blinker/)
* [pluggy is similar to our gcdt plugin mechanism](https://github.com/pytest-dev/pluggy)
* [glomex-credstash](https://github.com/glomex/glomex-credstash)
* [slack-webhooks](https://api.slack.com/incoming-webhooks)
* [hocon config format](https://github.com/typesafehub/config)
* [hocon in python](https://github.com/chimpler/pyhocon)
* [using datadog in python](https://github.com/DataDog/datadogpy)
* [using virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/)
