## gcdt-datadog-integration plugin

The original usecase for the gcdt_datadog_integration was to get usage data from gcdt executions. So we get some idea on frequency and gcdt utilization. We still use metrics with the datadog gcdt-dashboard to concentrate our efforts on the relevant parts of gcdt.


### Related documents

* [datadog integration](https://github.com/DataDog/datadogpy)


### datadog integration plugin functionality

* send metrics and events according to tool and command
* provide context e.g. host, user, env, stack



### Configuration

`datadog.api_key` is provided via secret lookup:

``` js
'gcdt_datadog_integration': {
    'datadog_api_key': 'lookup:secret:datadog.api_key'
},
```
