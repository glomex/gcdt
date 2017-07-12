## yugen command

`yugen` (幽玄 from Japanese: “dim”, “deep” or “mysterious”) is gcdts API Gateway deployment tool.

### Related documents

* [AWS API Gateway service](https://aws.amazon.com/api-gateway/)

### Usage

To see available commands, call this:
```bash
$ yugen
Usage:
        yugen deploy
        yugen delete -f
        yugen export
        yugen list
        yugen apikey-create <keyname>
        yugen apikey-list
        yugen apikey-delete
        yugen version
```
#### deploy
creates/updates an API from a given swagger file

#### export
exports the API definition to a swagger file

#### list
lists all existing APIs

#### apikey-create
creates an API key

#### apikey-list
lists all existing API keys

#### apikey-delete
deletes an API key

#### version
will print the version of gcdt you are using

### Folder Layout

`swagger.yaml` -> API definition in swagger with API Gateway extensions

`api.conf` -> settings for the API which is needed for wiring

```json
"api": {
    "name": "dp-dev-serve-api-2",
    "description": "description",
    "targetStage": "dev",
    "apiKey": "xxx"
}

"lambda": {

    "entries": [
      {
        "name": "dp-dev-serve-api-query",
        "alias": "ACTIVE"
      },
      {
        "name": "dp-dev-serve-api-query-elasticsearch",
        "alias": "ACTIVE"
      }
    ]

}
```

#### Setting the ENV variable

You you need to set an environment variable "ENV" which indicates the account/staging area you want to work with. This parameter tells the tools which config file to use. For example if you want to set the environment variable ENV to 'DEV' you can do that as follows:
``` bash
export ENV=DEV
```
