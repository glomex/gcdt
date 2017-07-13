## gcdt plugin mechanism

The previous chapter gave an overview on the gcdt plugin system so please make sure that you have read through that one. This section goes into more detail in how the gcdt plugin mechanism works. So you can customize plugins or even write new ones.

gcdt plugins are standard python packages which are installed separately. How to do this is covered in the previous chapter [plugin overview](http://gcdt.readthedocs.io/en/latest/gcdt_plugins/10_overview.html). To understand how the plugin mechanism works one must know about the `gcdt lifecycle` which is covered in the next section.

If a gcdt command is entered on the command line things are processed in the following order:

* Python interpreter loads the gcdt package
* CLI options and arguments are parsed
* we check if any relevant plugins are installed (details in `plugin entry_points`)
* relevant plugins are loaded and check if they comply to gcdt-plugin structure.
* register() function of each plugin is called.
* then the gcdt lifecycle is executed
* each lifecycle step fires an event which we call `signal`


### Anatomy of a plugin

Each gcdt-plugin must implement `register()` and `deregister()` functions to be a valid gcdt-plugin that can be used. Note how the `register()` function connects the plugin function `say_hello` with the `initialized` lifecycle step. `deregister()` just disconnects the plugin functionality from the gcdt lifecycle.

``` python
def say_hello(context):
    """
    :param context: The boto_session, etc.. say_hello plugin needs the 'user'
    """
    print('MoinMoin %s!' % context.get('user', 'to you'))

...

def register():
    """Please be very specific about when your plugin needs to run and why.
    E.g. run the sample stuff after at the very beginning of the lifecycle
    """
    gcdt_signals.initialized.connect(say_hello)
    gcdt_signals.finalized.connect(say_bye)


def deregister():
    gcdt_signals.initialized.disconnect(say_hello)
    gcdt_signals.finalized.disconnect(say_bye)
```

Handing in information to your plugin functions. Look into gcdt.gcdt_signals for details.

``` python
def my_plug_function(params):
    """
    :param params: context, config (context - the env, user, _awsclient, etc..
                   config - The stack details, etc..)
    """
    context, config = params
    # implementation here
    ...
```

All gcdt lifecycle steps provide the `(context, config)` tuple besides `initialized` and `finalized`. These two only provide the context.

The same lifecycle & signals mechanism applies to gcdt hooks. So if you ever wondered how gcdt hooks are work - now you know.


### Overview of the gcdt lifecycle

The gcdt lifecycle is the essential piece of the gcdt tool core. It is like the clockwork of a watch. The gcdt lifecycle makes sure that everything is executed in the right order and everything works together like commands, hooks, plugins, etc.

The gcdt lifecycle is generic. This means the gcdt lifecycle is the same for each and every gcdt tool. But it is possible that a tool does not need a certain lifecycle step to it just skips it. For example there is no bundling for kumo(, yet?).

The coarse grained gcdt lifecycle looks like that:

![gcdt_lifecycle](/docs/_static/images/gcdt_lifecycle.png)

If during processing of a lifecycle an error occurs then the processing stops.


### List of gcdt signals

The list of gcdt signals you can use in plugins or hooks:

* initialized - after reading arguments and context
* config_read_init
* config_read_finalized
* lookup_init
* lookup_finalized
* config_validation_init
* config_validation_finalized
* bundle_pre - we need this signal to implement the prebundle-hook
* bundle_init
* bundle_finalized
* command_init
* command_finalized
* error
* finalized

The order of this list also represents the order of the lifecycle steps with in the gcdt lifecycle.


### Developing plugins

If you want to develop a plugin to integrate some service or to optimize the configuration for your environment we recommend that you "fork" the say_hello plugin so you have the right structure and start from there.

If you need help developing your plugin or want to discuss your plans and get some feedback please don't be shy. The SRE squad is here to help.


### Testing a plugin

Testing a gcdt plugin should be easy since its code is decoupled from gcdt core. It is a good practice to put the tests into the `tests` folder. Also please prefix all your test files with `test_` in this way pytest can pick them up.
Please make sure that your plugin test coverage is on the save side of 80%.
