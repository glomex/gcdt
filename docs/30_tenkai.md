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

```text
codedeploy {
    applicationName = "mep-dev-cms-stack2-mediaExchangeCms-F5PZ6BM2TI8",
    deploymentGroupName = "mep-dev-cms-stack2-mediaExchangeCmsDg-1S2MHZ0NEB5MN",
    deploymentConfigName = "CodeDeployDefaultemplate.AllAtOnce01"
    artifactsBucket = "7finity-portal-dev-deployment"
}
```


## tenkai configuration


### add stack_output.yml to your tenkai bundle

If you need a convenient way of using the stack output during codedeploy on your instance then you can use this feature. 

`tenkai` adds a `stack_output.yml` to the bundle artifact if you add the following configuration:

``` js
{
    'stack_output': 'lookup:stack:<your_stack_name>
    ...
}
```


#### Setting the ENV variable

For example if you want to set the environment variable ENV to 'DEV' you can do that as follows:

``` bash
export ENV=DEV
```

