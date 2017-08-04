## gcdt-config-reader plugin 

Read config from files in json, python or yaml format.
There is a section called `overview on configuration` above. Please make sure you have that one covered.


### Related documents

* [JSON](https://en.wikipedia.org/wiki/JSON)
* [YAML](https://en.wikipedia.org/wiki/YAML)


### json configuration files

The gcdt_config_reader plugin allows us to have configurations in json format.

The configuration files are environment specific. This means the config file looks like gcdt_<env>.json` where <env> stands for the environment you use (some thing like dev, stage, prod, etc.).


### yaml configuration files

The gcdt_config_reader plugin allows us to have configurations in `yaml` format.

The configuration files are environment specific. This means the config file looks like gcdt_<env>.yaml` where <env> stands for the environment you use (some thing like dev, stage, prod, etc.).


### python configuration files

The gcdt_config_reader plugin allows us to have configurations in python format (with a .py extension).

The configuration files are environment specific. This means the config file looks like gcdt_<env>.py` where <env> stands for the environment you use (some thing like dev, stage, prod, etc.).

The python configuration files have a few specifics which are documented here.

The python configuration only work if they follow the convention to implement a `generate_config()` function. The `generate_config()` needs to return a dictionary with the configuration. Please follow the configuration structure described below.
  
``` python
def generate_config():
    return CFG
```

You can also use hooks in the python config files. Just implement the `register`, `deregister` like they are described in the plugin section to make that work.


### gcdtignore patterns

gcdt supports multiple ways of ignoring files from bundling. The file format of pattern files is the same as gitignore files. This means you can use wildcards to exclude files from bundling like for example `*.pyc`. This is currently relevant for the gcdt tools `tenkai` and `ramuda`.

The following files are supported:

* .ramudaignore - in the user home directory
* .gcdtignore - in the current directory
* .npmignore - in the current directory

Alternatively you can provide the ignore pattern with your `gcdt_<env>.json` config file:

``` js
{
    "gcdtignore": ["*.pyc", "trash"]
    ...
}
```

On a more technical note: all ignore patterns you provide are consolidated by the config reader and provided to plugins and tools as `config['gcdtignore']`.


### reference to base config file

The gcdt_config_reader plugin supports a `baseconfig` property which gives a basepath. This works with all supported config file formats like json, yaml and .py config files.

``` json
{
  "baseconfig": "baseconfig",
  "ramuda": {
    "lambda": {
      "runtime": "nodejs4.3",
  ...
```

With that you can for example implement the following config structure with your config files:
 
``` text
baseconfig.json
-> gcdt_dev.json
-> gcdt_stage.json
```

In this sample `baseconfig.json` contains all common config values for all environments. `gcdt_dev.json` contains only values specific for the development environment (same with `gcdt_stage.json`). Config values can be overridden by the dependent `gcdt_<env>.json` file, too.
