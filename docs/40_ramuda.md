## ramuda command

`ramuda` (ラムダ from Japanese: lambda) is gcdts AWS lambda deployment tool.


### Related documents

* [AWS Lambda service](https://aws.amazon.com/lambda/)


### Usage

To see available commands, call this:

```bash
$ ramuda
Usage:
        ramuda clean
        ramuda bundle
        ramuda deploy
        ramuda list
        ramuda metrics <lambda>
        ramuda wire
        ramuda unwire
        ramuda delete -f <lambda>
        ramuda rollback <lambda> [<version>]
        ramuda version
```
#### clean
removes local bundle files.

#### bundle
zips all the files belonging to your lambda according to your config and requirements.txt and puts it in your current working directory as `bundle.zip`. Useful for debugging as you can still provide different environments.

#### deploy
deploys a lambda function to AWS. If the lambda function is non-existent it will create a new one. For an existing lambda function it checks whether code has changed and updates accordingly. In any case configuration will be updated and an alias called "ACTIVE" will be set to this version.

#### list
lists all existing lambda functions including additional information like config and active version:
```bash
dp-dev-store-redshift-create-cdn-tables
	Memory: 128
	Timeout: 180
	Role: arn:aws:iam::644239850139:role/lambda/dp-dev-store-redshift-cdn-LambdaCdnRedshiftTableCr-G7ME657RXFDB
	Current Version: $LATEST
	Last Modified: 2016-04-26T18:03:44.705+0000
	CodeSha256: KY0Xk+g/Gt69V0siRhgaG7zWbg234dmb2hoz0NHIa3A=
```

#### metrics
displays metric for a given lambda:
```bash
dp-dev-ingest-lambda-cdnnorm
	Duration 488872443
	Errors 642
	Invocations 5202
	Throttles 13
```

#### wire
"wires" the lambda function to its event configuration. This actually activates the lambda function.

#### unwire
delets the event configuration for the lambda function

#### delete
deletes a lambda function

#### rollback
sets the active version to ACTIVE -1 or to a given version

#### version
will print the version of gcdt you are using


### Folder Layout

lambda_ENV.conf -> settings for Lambda function

```text
lambda {
  name = "dp-dev-store-redshift-load"
  description = "Lambda function which loads normalized files into redshift"
  role = "arn:aws:iam::644239850139:role/lambda/dp-dev-store-redshift-cdn-lo-LambdaCdnRedshiftLoad-DD2S84CZFGT4"

  handlerFunction = "handler.lambda_handler"
  handlerFile = "handler.py"
  timeout = "180"
  memorySize = "128"
  events {
    s3Sources = [
        { bucket = "dp-dev-store-cdn-redshift-manifests", type = "s3:ObjectCreated:*", suffix = ".json" },
        { 
            bucket = "dp-dev-store-cdn-redshift-manifests",
            type = "s3:ObjectCreated:*",
            prefix = "folder",
            suffix = ".gz",
            ensure="exists"
         }
    ]
        timeSchedules = [
           {
               ensure = "exists",
               ruleName = "time-event-test-T1",
               ruleDescription = "run every 5 min from 0-5 UTC",
               scheduleExpression = "cron(0/5 0-5 ? * * *)"
           },
        ]
  }
  vpc  {
    subnetIds = ["subnet-87685dde", "subnet-9f39ccfb", "subnet-166d7061"]
    securityGroups = ["sg-ae6850ca"]
  }
}

bundling {
  zip = "bundle.zip"
  preBundle = ["../bin/first_script.sh", "../bin/second_script.sh"]
  folders = [
    { source = "../redshiftcdnloader", target = "./redshiftcdnloader"}
    { source = "psycopg2-linux", target = "psycopg2" }
  ]
}

deployment {
  region = "eu-west-1",
  artifactBucket = "7finity-$PROJECT-deployment"
}

```

### configuration

#### user configuration in ~/.gcdt

The .gcdt config file resides in your home folder and is created with "$ gcdt configure" as described above.
We use .gcdt config file also for user specific configuration:

```text
ramuda {
  failDeploymentOnUnsuccessfulPing = true
}
```

*failDeploymentOnUnsuccessfulPing*: ramuda deploy command fails if the lambda function does not implement ping or ping fails.


#### lambda configuration

settings_<env>.conf -> settings for your code


#### S3 upload
ramuda can upload your lambda functions to S3 instead of inline through the API.
To enable this feature add this to your lambda.conf:

deployment {
region = "eu-west-1",
    artifactBucket = "7finity-$PROJECT-deployment"
}

You can get the name of the bucket from Ops and it should be part of the stack outputs of the base stack in your account (s3DeploymentBucket).


#### Setting the ENV variable

For example if you want to set the environment variable ENV to 'DEV' you can do that as follows:

``` bash
export ENV=DEV
```


### runtime support

gcdt supports the `nodejs4.3`, `nodejs6.10`, `python27`, `python36` runtimes.

Add the runtime config to the `lambda` section of your gcdt configuration. 

``` js
    "runtime": "nodejs4.3"
```

At this point the following features are implemented:

* install dependencies before bundling (dependencies are defined in package.json)
* bundling (bundle the lambda function code and dependencies)
* deployment (the nodejs4.3 lambda function is setup with the nodejs4.3 runtime)
* configuration (bundles `settings_<env>.conf` file for your environments)
* nodejs support is tested by our automated gcdt testsuite

Note: for this to work you need to **have npm installed** on the machine you want to run the ramuda bundling!


#### Defining dependencies for your NodeJs lambda function

A sample `package.json` file to that defines a dependency to the `1337` npm module:

```json
{
  "name": "my-sample-lambda",
  "version": "0.0.1",
  "description": "A very simple lambda function",
  "main": "index.js",
  "dependencies": {
    "1337": "^1.0.0"
  }
}
```


#### Sample NodeJs lambda function

From using lambda extensively we find it a good practise to implement the `ping` feature. With the ping `ramdua` automatically checks if your code is running fine on AWS.
 
 Please consider to implement a `ping` in your own lambda functions:
 
 ```javascript
var l33t = require('1337')


exports.handler = function(event, context, callback) {
    console.log( "event", event );

    if (typeof(event.ramuda_action) !== "undefined" && event.ramuda_action == "ping") {
        console.log("respond to ping event");
        callback(null, "alive");
    } else {
        console.log(l33t('glomex rocks!'));  // 910m3x r0ck5!
        callback();  // success
    }
};
```


#### Environment specific configuration for your lambda function

Please put the environment specific configuration for your lambda function into a `settings_<env>.conf` file.
