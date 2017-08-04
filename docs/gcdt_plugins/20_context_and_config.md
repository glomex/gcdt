## Overview on configuration

Configuration and configuration file formats are very dear to us and we already know to you, too. For example the data_platform squad likes to use multiple tool specific hocon files so this functionality is provided by the `glomex_config_reader?. Other squads like to have all the configuration for a service environment in one single config file (gcdt_config_reader).

Regarding configuration file formats many things are possible and it should be very simple to implement your specific requirements as a plugin so you could use XML or INI format. Talk to us and do not shy away from good old json config.


### Structure of the configuration (internal representation)

The datastructure gcdt uses to internally represent the configuration basically is json compatible.

We have configuration on the following levels:

* top-level
* tool-level (tools are kumo, tenkai, ramuda, yugen)
* plugin specific configuration

``` js
{
    'kumo': {
        ...
    },
    'tenkai': {
        ...
    },
    'ramuda': {
        ...
    },
    'yugen': {
        ...
    },
    'plugins' {
        'plugin_a': {
            ...
        },
        ...
    }
}
```


### Multiple levels of gcdt configuration

Configuration is assembled in multiple levels:

![gcdt configuration defaults](_static/images/gcdt_configuration.png "gcdt configuration defaults")

The multiple levels of configurations represent different stages in the lifecycle process. This allows to have a very generic "catch-all" configuration but to override this configuration in specific cases when we have more specific information. Like when using a plugin. For example the glomex_config_reader works on hocon files so it looks for files with a `.conf` extension whereas the gcdt_config_reader looks for `.json` config files.


### Context

The gcdt `context` is the "internal" datastructure gcdt is using to process the CLI command that need to be executed. So for instance each plugin or hook can find out about the `tool`, `command`, or `env` it is currently processing. With the context we follow the convention to prefix private attributes with an '_' like with the `_awsclient` that plugins use to access AWS services but `_awsclient` does not show up in the slack or datadog notification.

``` json
{
  'version': '0.1.426',
  'command': 'preview',
  '_awsclient': <gcdt.gcdt_awsclient.AWSClient object at 0x10291a490>,
  'env': 'dev',
  '_arguments': {
    '--override-stack-policy': False,
    '-f': False,
    'delete': False,
    'deploy': False,
    'dot': False,
    'generate': False,
    'list': False,
    'preview': True,
    'version': False
  },
  'tool': 'kumo',
  'plugins': [
    'gcdt-config-reader',
    'gcdt-bundler',
    'gcdt-say-hello',
    'glomex-config-reader',
    'gcdt-slack-integration',
    'glomex-checks',
    'gcdt-gru',
    'gcdt-datadog-integration',
    'gcdt-lookups'
  ],
  'user': 'fin0007m'
}
```
