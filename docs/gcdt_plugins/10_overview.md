## Overview

This sections provides and overview on the gcdt-plugin system. It covers everything necessary to understand how it works at a high level.


### Plugin system key functions

Main functionality of the gcdt plugin system is to provide means so gcdt can be customized and extended without changing the core functionality. This is necessary for example in case not everybody uses slack or datadog. In this situation one can just not use the plugin or use a plugin which supports an alternate service.

Plugins are added to gcdt via python packages. The following section covers how to do that.

The gcdt plugin mechanism also encapsulates the plugin code in a way that it is separated from gcdt core. This enables us to change and test a plugin as a component independent from gcdt core. More details about the `plugin mechanism` are covered in the next chapter. 


### Plugin installation

Plugins are maintained as standard python packages. Just install plugins you want via `pip install <plugin_name>`. Same idea applies to removing plugins from a project setup. Using `pip uninstall <plugin_name>` removes the plugin.

A more sophisticated way of doing that which goes well with CI/CD is to simply add your gcdt plugins to your projects `requirements_gcdt.txt` file. Especially if you need more tools and plugins this makes setting up your CI environment easy and reproducible. `pip install -r requirements.txt -r requirments_dev.txt` installs all the packages you need for your service and for developing it.


### Plugin configuration

Configuration for a plugin are specific for that plugin so please consult the plugins documentation for specific configuration options. General mechanism is that you add the configuration for the plugin to your `gcdt_<env>.json` file. Add a section with the plugin name like in the following snippet:

``` js
    ...
    'plugins': {
        ...
        'gcdt_slack_integration': {
            'slack_webhook': 'lookup:secret:slack.webhook:CONTINUE_IF_NOT_FOUND'
        },
        ...
    }
```


### Plugin descriptions

The following table lists the plugins and gives a brief overview what each plugin is used for.

Plugin | Description
------ | -----------
gcdt_config_reader | read configuration files in json, python, or yaml format
glomex_config_reader | read hocon configuration files
gcdt_lookup | lookup information related to your AWS account
gcdt_bundler | create code bundles for tenkai and ramuda.
gcdt_say_hello | simple plugin to demonstrate how plugins work / are developed
gcdt_slack_integration | send deployment status information to slack
gcdt_datadog_integration | send deployment metrics and events to datadog

Please refer to detailed plugin's documentation later in this document folder for detailed information about that plugin.

Later we are going to put plugins in separate repositories so they can have independent owners and development / release cycles. With that we move the detailed plugin documentation to the plugin README and documentation.
