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
        ramuda bundle [--keep] [-v]
        ramuda deploy [--keep] [-v]
        ramuda list
        ramuda metrics <lambda>
        ramuda info
        ramuda wire [-v]
        ramuda unwire [-v]
        ramuda delete [-v] -f <lambda> [--delete-logs]
        ramuda rollback [-v] <lambda> [<version>]
        ramuda ping [-v] <lambda> [<version>]
        ramuda invoke [-v] <lambda> [<version>] [--invocation-type=<type>] --payload=<payload> [--outfile=<file>]
        ramuda logs <lambda> [--start=<start>] [--end=<end>] [--tail]
        ramuda version

Options:
-h --help               show this
-v --verbose            show debug messages
--keep                  keep (reuse) installed packages
--payload=payload       '{"foo": "bar"}' or file://input.txt
--invocation-type=type  Event, RequestResponse or DryRun
--outfile=file          write the response to file
--delete-logs           delete the log group and contained logs
--start=start           log start UTC '2017-06-28 14:23' or '1h', '3d', '5w', ...
--end=end               log end UTC '2017-06-28 14:25' or '2h', '4d', '6w', ...
--tail                  continuously output logs (can't use '--end'), stop 'Ctrl-C'
```

#### clean
removes local bundle files.

#### bundle
zips all the files belonging to your lambda according to your config and requirements.txt and puts it in your current working directory as `bundle.zip`. Useful for debugging as you can still provide different environments.

#### deploy

Deploy an AWS Lambda function to AWS. If the lambda function is non-existent it will create a new one.

For an existing lambda function ramuda checks whether the hashcode of the bundle has changed and updates the lambda function accordingly. This feature was added to ramuda so we are able to compare the hashcodes locally and save time for bundle uploads to AWS.

This only works if subsequent deployments are executed from the same virtualenv (and same machine). The current implementation of the gcdt-bundler starts every deployment with a fresh virtualenv. If you want the hashcode comparison you need to provide the `--keep` option. With the '--keep' option the virtualenv is preserved. Otherwise the hashcodes of the ramuda code bundles will be different and the code will be deployed.

If you can not reuse ('--keep') the virtualenv for example in case you deploy from different machines you need to use `git` to check for code changes and skip deployments accordingly.

In any case configuration will be updated and an alias called "ACTIVE" will be set to this version.

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

If you use the `--delete-logs` the cloudwatch log group associated to the AWS Lambda function is deleted including log entries, too. This helps to save cost for items used in testing.

#### rollback
sets the active version to ACTIVE -1 or to a given version

#### invoke

In this section, you invoke your Lambda function manually using the `ramuda invoke` command.

``` bash
$ ramuda invoke my_hello_world \
--invocation-type RequestResponse \
--payload '{"key1":"value1", "key2":"value2", "key3":"value3"}'
```

If you want you can save the payload to a file (for example, input.txt) and provide the file name as a parameter:

``` bash
$ ramuda invoke my_hello_world \
--invocation-type RequestResponse \
--payload file://input.txt
```

The preceding invoke command specifies RequestResponse as the invocation type, which returns a response immediately in response to the function execution. Alternatively, you can specify Event as the invocation type to invoke the function asynchronously.

#### logs

The `ramuda logs` command provides you with convenient access to log events emitted by your AWS Lambda function.

The command offers '--start' and '--end' options where you can filter the log events to your specification. You can use human readable dates like '2017-07-24 14:00:00' or you can specify dates in the past relative to `now` using '1m', '2h', '3d', '5w', etc.

``` bash
$ ramuda logs ops-dev-captain-crunch-slack-notifier --start=1d
MoinMoin fin0007m!
2017-07-07
07:00:32  START RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8 Version: $LATEST
07:00:36  END RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8
07:00:36  REPORT RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8        Duration: 4221.50 ms    Billed Duration: 4300 ms        Memory Size: 128 MB     Max Memory Used: 43 MB
Bye fin0007m. Talk to you soon!
```

The '--start' option has a default of '1d'. This means if you run `ramuda logs <your-function-name>` you get the log output of your function for the last 24 hours.

``` bash
$ ramuda logs ops-dev-captain-crunch-slack-notifier
MoinMoin fin0007m!
2017-07-07
07:00:32  START RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8 Version: $LATEST
07:00:36  END RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8
07:00:36  REPORT RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8        Duration: 4221.50 ms    Billed Duration: 4300 ms        Memory Size: 128 MB     Max Memory Used: 43 MB
Bye fin0007m. Talk to you soon!
```

You can use `ramuda logs` to **tail** the log output of your lambda function. The default start date in tail mode is 5 minutes before. You can specify any past start date in tail mode but you can not specify an '--end' option in tail mode. To exit the `ramuda logs` tail mode use `Ctrl-C`.

``` bash
$ ramuda logs ops-dev-captain-crunch-slack-notifier --start=1d --tail
MoinMoin fin0007m!
Use 'Ctrl-C' to exit tail mode
2017-07-07
07:00:32  START RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8 Version: $LATEST
07:00:36  END RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8
07:00:36  REPORT RequestId: f75cd7de-62e1-11e7-937d-ef5726c6f5c8        Duration: 4221.50 ms    Billed Duration: 4300 ms        Memory Size: 128 MB     Max Memory Used: 43 MB
^CReceived SIGINT signal - exiting command 'ramuda logs'
```

#### version
will print the version of gcdt you are using

### Folder Layout

### Sample config file

sample gcdt_dev.json file:

```text
{
  "ramuda": {
    "lambda": {
      "name": "dp-dev-store-redshift-load",
      "description": "Lambda function which loads normalized files into redshift",
      "role": "arn:aws:iam::644239850139:role/lambda/dp-dev-store-redshift-cdn-lo-LambdaCdnRedshiftLoad-DD2S84CZFGT4",
      "handlerFunction": "handler.lambda_handler",
      "handlerFile": "handler.py",
      "timeout": "180",
      "memorySize": "128",
      "events": {
        "s3Sources": [
          {
            "bucket": "dp-dev-store-cdn-redshift-manifests",
            "type": "s3:ObjectCreated:*",
            "suffix": ".json"
          },
          {
            "bucket": "dp-dev-store-cdn-redshift-manifests",
            "type": "s3:ObjectCreated:*",
            "prefix": "folder",
            "suffix": ".gz",
            "ensure": "exists"
          }
        ],
        "timeSchedules": [
          {
            "ensure": "exists",
            "ruleName": "time-event-test-T1",
            "ruleDescription": "run every 5 min from 0-5 UTC",
            "scheduleExpression": "cron(0/5 0-5 ? * * *)"
          }
        ]
      },
      "vpc": {
        "subnetIds": [
          "subnet-87685dde",
          "subnet-9f39ccfb",
          "subnet-166d7061"
        ],
        "securityGroups": [
          "sg-ae6850ca"
        ]
      }
    },
    "bundling": {
      "zip": "bundle.zip",
      "preBundle": [
        "../bin/first_script.sh",
        "../bin/second_script.sh"
      ],
      "folders": [
        {
          "source": "../redshiftcdnloader",
          "target": "./redshiftcdnloader"
        },
        {
          "source": "psycopg2-linux",
          "target": "psycopg2"
        }
      ]
    },
    "deployment": {
      "region": "eu-west-1",
      "artifactBucket": "7finity-$PROJECT-deployment"
    }
  }
}
```

### ramuda configuration as part of the gcdt_<env>.json file

#### log retention

Possible values for the log retention in days are: 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, and 3653.

``` json
"lambda": {
    ...
    "logs": {
        "retentionInDays": 90
    }
}
```

#### S3 upload
ramuda can upload your lambda functions to S3 instead of inline through the API.
To enable this feature add this to the "ramuda" section of your `gcdt_<env>.json` config file:

``` json
"deployment": {
    "region": "eu-west-1",
    "artifactBucket": "7finity-$PROJECT-deployment"
}
```

You can get the name of the bucket from Ops and it should be part of the stack outputs of the base stack in your account (s3DeploymentBucket).


### Setting the ENV variable

You you need to set an environment variable "ENV" which indicates the account/staging area you want to work with. This parameter tells the tools which config file to use. For example if you want to set the environment variable ENV to 'DEV' you can do that as follows:
``` bash
export ENV=DEV
```

### runtime support

gcdt supports the `nodejs4.3`, `nodejs6.10`, `python2.7`, `python3.6` runtimes.

Add the runtime config to the `lambda` section of your gcdt configuration.

``` json
    "runtime": "nodejs4.3"
```

At this point the following features are implemented:

* install dependencies before bundling (dependencies are defined in package.json)
* bundling (bundle the lambda function code and dependencies)
* deployment (the nodejs4.3 lambda function is setup with the nodejs4.3 runtime)
* configuration (bundles `settings_<env>.conf` file for your environments)
* nodejs support is tested by our automated gcdt testsuite
* if no runtime is defined gcdt uses the default runtime `python2.7`

Note: for this to work you need to **have npm installed** on the machine you want to run the ramuda bundling!

#### AWS Lambda environment variables

Ramuda supports AWS Lambda environment variables. You can specify them within the `lambda` section.

``` json
    ...
    "environment": {
        "MYVALUE": "FOO"
    }
```

More information you can find in [AWS docs](http://docs.aws.amazon.com/lambda/latest/dg/env_variables.html).

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

### Environment specific configuration for your lambda functions

Please put the environment specific configuration for your lambda function into a `gcdt_<env>.json` file. For most teams a good convention would be to maintain at least 'dev', 'qa', and 'prod' envs.
