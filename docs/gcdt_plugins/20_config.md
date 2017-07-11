## Overview on configuration

Configuration and configuration file formats are very dear to us and we already know to you, too. For example the DIS squad likes to use multiple tool specific hocon files so this functionality is provided by the glomex_config_reader. Other squads like to have all the configuration for a service environment in one single config file (gcdt_config_reader).

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

![gcdt configuration defaults](/_static/images/gcdt_configuration.png "gcdt configuration defaults")

The multiple levels of configurations represent different stages in the lifecycle process. This allows to have a very generic "catch-all" configuration but to override this configuration in specific cases when we have more specific information. Like when using a plugin. For example the glomex_config_reader works on hocon files so it looks for files with a `.conf` extension whereas the gcdt_config_reader looks for `.json` config files.
