# Setup gcdt build jobs

## SeedJob on Jenkins

The SeedJob is created manually on the infra - Jenkins in the "glomex-cloud-deployment-tools" folder (see screenshots).
The SeedJob is currently triggered manually to configure the gcdt build jobs from the github repo develop branch (infrastructure/ci/jobs folder). If necessary the SeedJob configuration can easyly changed to trigger the job setup automatically.

![SeedJob config](./gcdt-seedjob.png?raw=true)
![SeedJob config](./gcdt-seedjob2.png?raw=true)


## docu on how to setup the psd-jenkins-fontend user:

you need two forms of github access (in global credentials):

* user + password
* github api token for the same user

The setup can be tricky so please read the following docu:

https://github.com/glomex/data-platform/tree/develop/operations/jenkins


## necessary plugins

* Job DSL
* Throttle Concurrent Builds Plug-in (throttle-concurrents) 
* GitHub API Plugin
* GitHub plugin
* GitHub Pull Request Builder (this has references to other required plugins...)
* Credentials Binding Plugin
* envinject
* Slack Notification Plugin


## on your github repo

You need to setup the webhook for your jenkins within your repo. Go to https://github.com/glomex/glomex-cloud-deployment-tools and open the Webhooks tab.

format of the webhook: "http://<Name of Jenkins server>:8080/github-webhook/"

https://infra-jenkins01-prod.infra.glomex.cloud/github-webhook/

Add a new webhook for the two targets
https://jenkins-webhook.YOUR_ENVIRONMENT.dp.glomex.cloud/github-webhook/
https://jenkins-webhook.YOUR_ENVIRONMENT.dp.glomex.cloud/ghprbhook/ Pull-Request triggering

here some docu:
https://thepracticalsysadmin.com/setting-up-a-github-webhook-in-jenkins/


# on the executor

$ git config --list

set the git user name and email... TODO


