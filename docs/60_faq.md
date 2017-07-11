## Frequently Asked Questions (faq)


### Homebrew Python

If you installed Python via Homebrew on OS X and get this error:

``` bash
must supply either home or prefix/exec-prefix -- not both
```

You can find a solution on [here](http://stackoverflow.com/questions/24257803/distutilsoptionerror-must-supply-either-home-or-prefix-exec-prefix-not-both)

### Python package errors

**Please ensure that you have the latest version of `pip`, `setuptools` and `virtualenv`**

If you have error like this:
```bash
pip._vendor.pkg_resources.DistributionNotFound:
```
or
```bash
pkg_resources.DistributionNotFound: regex==2017.6.07
```
you should update your `pip` and `virtualenv` packages
```bash
$ pip install pip --upgrade
$ pip install virtualenv --upgrade
```

### Bundling error

This error is usually caused by not having installed the `gcdt-bundler` plugin:
```python
(.python) root@:/app# AWS_PROFILE=superuser-dev ENV=qa ramuda deploy
ERROR: u'_zipfile'
ERROR: u'_zipfile'
Traceback (most recent call last):
  File "/root/.python/bin/ramuda", line 11, in <module>
    sys.exit(main())
  File "/root/.python/local/lib/python2.7/site-packages/gcdt/ramuda_main.py", line 255, in main
    dispatch_only=['version', 'clean']))
  File "/root/.python/local/lib/python2.7/site-packages/gcdt/gcdt_lifecycle.py", line 195, in main
    return lifecycle(awsclient, env, tool, command, arguments)
  File "/root/.python/local/lib/python2.7/site-packages/gcdt/gcdt_lifecycle.py", line 142, in lifecycle
    raise(e)
KeyError: u'_zipfile'
```
You need to add `gcdt-bundler` into *requirements_gcdt.txt* and do:
```bash
$ pip install -U -r requirements_gcdt.txt
```

### Missing configuration error

After updating `gcdt` to the latest version you saw such error:
```bash
Configuration missing for ‘kumo’
```
This error appear if you used `hocon` based configs without installed `glomex-config-reader` plugin. You can install it or use [conf2json](http://sre-docs.glomex.cloud/glomex-config-reader/userguide/40_glomex_config_reader.html#command-conf2json) util (only for glomex users) to transform your `hocon` configs into `json` one.

### Environment variable error

If you run any `gcdt` commands (kumo, tenkai, ramuda etc) and have such error:
```
ERROR: 'ENV' environment variable not set!
```
please be sure that you provide the correct environment variables (ENV=PROD/DEV/etc.)
```bash
$ export ENV=DEV
```

### Using hooks in gcdt

We implemented hooks in gcdt similar to the plugin mechanism.

You can use hooks in gcdt in the following places:

* use hooks in a `cloudformation.py` template
* use hooks in a `gcdt_<env>.py` config file
* use hooks in a `hookfile.py`. Please specify the location of the `hookfile` in your config file.

For details on gcdt_lifecycle and gcdt_signals please take a look into the gcdt-plugins section of this documentation.
