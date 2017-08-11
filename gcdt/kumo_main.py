#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The 'kumo' tool is used to deploy infrastructure CloudFormation templates
to AWS cloud.
"""

from __future__ import unicode_literals, print_function
import os
import sys
from collections import OrderedDict
import json
import time
from tempfile import NamedTemporaryFile

from clint.textui import colored
from pyspin.spin import Default, Spinner

from . import utils
from .kumo_core import get_parameter_diff, delete_stack, \
    deploy_stack, write_template_to_file, list_stacks, create_change_set, \
    describe_change_set, load_cloudformation_template, call_pre_hook, \
    generate_template, stop_stack, start_stack
from .kumo_viz import cfn_viz, svg_output
from .gcdt_cmd_dispatcher import cmd
from . import gcdt_lifecycle


# creating docopt parameters and usage help
DOC = '''Usage:
        kumo deploy [--override-stack-policy] [-v]
        kumo list [-v]
        kumo delete -f [-v]
        kumo generate [-v]
        kumo preview [-v]
        kumo dot [-v]
        kumo stop [-v]
        kumo start [-v]
        kumo version

-h --help           show this
-v --verbose        show debug messages
'''


def load_template():
    """Bail out if template is not found.
    """
    cloudformation, found = load_cloudformation_template()
    if not found:
        print(colored.red('could not load cloudformation.py, bailing out...'))
        sys.exit(1)
    return cloudformation


@cmd(spec=['version'])
def version_cmd():
    utils.version()


@cmd(spec=['dot'])
def dot_cmd(**tooldata):
    context = tooldata.get('context')
    conf = tooldata.get('config')
    cloudformation = load_template()
    with NamedTemporaryFile(delete=False, mode='w') as temp_dot:
        cfn_viz(json.loads(
                generate_template(context, conf, cloudformation),
                object_pairs_hook=OrderedDict),
                parameters=conf,
                out=temp_dot)
        temp_dot.close()
        exit_code = svg_output(temp_dot.name)
        os.unlink(temp_dot.name)
        return exit_code


@cmd(spec=['deploy', '--override-stack-policy'])
def deploy_cmd(override, **tooldata):
    context = tooldata.get('context')
    conf = tooldata.get('config')
    awsclient = context.get('_awsclient')

    cloudformation = load_template()
    call_pre_hook(awsclient, cloudformation)

    if get_parameter_diff(awsclient, conf):
        print(colored.red('Parameters have changed. Waiting 10 seconds. \n'))
        print('If parameters are unexpected you might want to exit now: control-c')
        # Choose a spin style.
        spin = Spinner(Default)
        # Spin it now.
        for i in range(100):
            print(u'\r{0}'.format(spin.next()), end='')
            sys.stdout.flush()
            time.sleep(0.1)
        print('\n')

    exit_code = deploy_stack(awsclient, context, conf, cloudformation,
                             override_stack_policy=override)
    return exit_code


@cmd(spec=['delete', '-f'])
def delete_cmd(force, **tooldata):
    context = tooldata.get('context')
    conf = tooldata.get('config')
    awsclient = context.get('_awsclient')
    return delete_stack(awsclient, conf)


@cmd(spec=['generate'])
def generate_cmd(**tooldata):
    conf = tooldata.get('config')
    cloudformation = load_template()
    write_template_to_file(conf, generate_template({}, conf, cloudformation))
    return 0


@cmd(spec=['list'])
def list_cmd(**tooldata):
    context = tooldata.get('context')
    awsclient = context.get('_awsclient')
    list_stacks(awsclient)


@cmd(spec=['preview'])
def preview_cmd(**tooldata):
    context = tooldata.get('context')
    conf = tooldata.get('config')
    awsclient = context.get('_awsclient')
    cloudformation = load_template()
    get_parameter_diff(awsclient, conf)
    change_set, stack_name, change_set_type = \
        create_change_set(awsclient, context, conf, cloudformation)
    if change_set_type == 'CREATE':
        print('Stack \'%s\' does not exist.' % stack_name)
        print('`kumo deploy` would create the following resources:')
    else:
        print('`kumo deploy` would update the following resources:')
    describe_change_set(awsclient, change_set, stack_name)
    if change_set_type == 'CREATE':
        # we currently do not review stack creations!
        # so we delete the stack in "REVIEW" state
        # more details here: https://github.com/glomex/gcdt/issues/73
        delete_stack(awsclient, conf, feedback=False)


@cmd(spec=['stop'])
def stop_cmd(**tooldata):
    context = tooldata.get('context')
    conf = tooldata.get('config')
    awsclient = context.get('_awsclient')

    #cloudformation = load_template()

    exit_code = stop_stack(awsclient, conf)
    return exit_code


@cmd(spec=['start'])
def start_cmd(**tooldata):
    context = tooldata.get('context')
    conf = tooldata.get('config')
    awsclient = context.get('_awsclient')

    #cloudformation = load_template()

    exit_code = start_stack(awsclient, conf)
    return exit_code


def main():
    sys.exit(gcdt_lifecycle.main(DOC, 'kumo'))


if __name__ == '__main__':
    main()
