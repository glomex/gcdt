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
from tempfile import NamedTemporaryFile

from clint.textui import colored

from . import utils
from .kumo_core import print_parameter_diff, delete_stack, \
    deploy_stack, generate_template_file, list_stacks, create_change_set, \
    describe_change_set, load_cloudformation_template, call_pre_hook
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
        kumo version
        kumo dot [-v]

-h --help           show this
-v --verbose        show debug messages
'''


def load_template():
    """Bail out if template is not found.
    """
    cloudformation, found = load_cloudformation_template()
    if not found:
        print(colored.red('no cloudformation.py found, bailing out...'))
        sys.exit(1)
    return cloudformation


@cmd(spec=['version'])
def version_cmd():
    utils.version()


@cmd(spec=['dot'])
def dot_cmd(**tooldata):
    conf = tooldata.get('config')
    cloudformation = load_template()
    with NamedTemporaryFile(delete=False, mode='w') as temp_dot:
        cfn_viz(json.loads(cloudformation.generate_template(), object_pairs_hook=OrderedDict),
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
    print_parameter_diff(awsclient, conf)
    exit_code = deploy_stack(awsclient, conf, cloudformation,
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
    generate_template_file(conf, cloudformation)
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
    print_parameter_diff(awsclient, conf)
    change_set, stack_name = create_change_set(awsclient, conf,
                                               cloudformation)
    describe_change_set(awsclient, change_set, stack_name)


def main():
    sys.exit(gcdt_lifecycle.main(DOC, 'kumo'))


if __name__ == '__main__':
    main()
