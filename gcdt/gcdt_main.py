#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The 'gcdt' tool provides 'common' tasks.
"""
from __future__ import unicode_literals, print_function
import sys

from . import utils
from . import gcdt_lifecycle
from .gcdt_cmd_dispatcher import cmd
from banana.router import Router
#from banana.routes import run
from whaaaaat import color_print as cp


GCDT_GENERATOR_GROUP = 'gcdtgen10'

# creating docopt parameters and usage help
DOC = '''Usage:
        gcdt version
        gcdt list
        gcdt generate <generator>

-h --help           show this
'''


@cmd(spec=['version'])
def version_cmd():
    utils.version()


@cmd(spec=['generate', '<generator>'])
def generate_cmd(generator):
    insight = None
    env = {}
    router = Router(env, insight, group=GCDT_GENERATOR_GROUP)
    cp.yellow('\nMake sure you are in the directory you want to scaffold into.\n\n')

    #router.register_route('run', run)
    #router.navigate('run', generator)
    # in this simple routing scenario we can call the generator directly
    router.execute(generator)


@cmd(spec=['list'])
def list_cmd():
    router = Router(None, {}, group=GCDT_GENERATOR_GROUP)
    print('Installed gcdt generators:')
    for g in router.generators:
        print('  - %s' % g)


def main():
    sys.exit(gcdt_lifecycle.main(DOC, 'gcdt',
                                 dispatch_only=['version', 'generate', 'list']))


if __name__ == '__main__':
    main()
