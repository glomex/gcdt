## tenkai command

`tenkai` (展開 from Japanese: deployment) is gcdts codedeploy tool.


### Related documents

* [AWS Codedeploy service](https://aws.amazon.com/codedeploy/)


### Usage

To see available commands, call this:

```bash
$ tenkai
Usage:
        tenkai bundle [-v]
        tenkai deploy [-v]
        tenkai version

-h --help           show this
-v --verbose        show debug messages
```

#### deploy
bundles your code then uploads it to S3 as a new revision and triggers a new deployment


#### version
will print the version of gcdt you are using


### Folder Layout

codedeploy -> folder containing your deployment bundle

codedeploy_env.conf -> settings for your code

```json
"codedeploy": {
    "applicationName": "mep-dev-cms-stack2-mediaExchangeCms-F5PZ6BM2TI8",
    "deploymentGroupName": "mep-dev-cms-stack2-mediaExchangeCmsDg-1S2MHZ0NEB5MN",
    "deploymentConfigName": "CodeDeployDefaultemplate.AllAtOnce01",
    "artifactsBucket": "7finity-portal-dev-deployment"
}
```


### tenkai configuration

#### add stack_output.yml to your tenkai bundle

If you need a convenient way of using the stack output during codedeploy on your instance then you can use this feature.

`tenkai` adds a `stack_output.yml` to the bundle artifact if you add the following configuration:

``` js
{
    'stack_output': 'lookup:stack:<your_stack_name>'
    ...
}
```


#### Adding a settings.json file

tenkai supports a `settings` section. If it is used a `settings.json` file is added to the zip bundle containing the values. You can specify the settings within the `tenkai` section.
``` json
    ...
    "settings": {
        "MYVALUE": "FOO"
    }
```

You can use lookups like for the rest of the configuration. Note that the values are looked up BEFORE the the instance is deployed via codedeploy. If values change during the instance lifecycle it does not recognise the changes. For values that must be updated you should lookup the values in your code using for example credstash.

``` json
    ...
    "settings": {
        "accountId": "lookup:stack:infra-dev:AWSAccountId"
    }
```


#### Configure log group
In case `tenkai deploy` fails we attempt to provide the log output from the ec2 instance to ease your troubleshooting. The default log group is '/var/log/messages'. In case your ec2 instances are configured to log into another log group you can provide the necessary log group configuration to tenkai like this:

``` json
"tenkai": {
    ...
    "deployment": {
        "LogGroup": "/my/loggroup"
    }
}
```

Note: as a convention each ec2 instances has its own log stream with using the instanceId as name of the stream.


#### Setting the ENV variable

You you need to set an environment variable "ENV" which indicates the account/staging area you want to work with. This parameter tells the tools which config file to use. For example if you want to set the environment variable ENV to 'DEV' you can do that as follows:
``` bash
export ENV=DEV
```


### Signal handling

tenkai receives a SIGINT or SIGTERM signal during a deployment `stop_deployment` is called for the running deployment with `autoRollbackEnabled`.
