# -*- coding: utf-8 -*-
"""
Reusable docopt cmd decorator.
The order of cmd registration in your generator file matters. Please make sure
you place cmds from specific to less-specific to catch-all.
"""
from __future__ import unicode_literals, print_function


# based on https://github.com/finklabs/banana/blob/master/banana/docopt_cmd.py


# Details of the decorator mechanics:
# http://python-3-patterns-idioms-test.readthedocs.io/en/latest/PythonDecorators.html
class cmd(object):
    _specs = []  # list of tuples (spec, function)

    def __init__(self, spec):
        """
        If there are decorator arguments, the function
        to be decorated is not passed to the constructor!
        """
        self._spec = spec

    def __call__(self, func):
        """
        If there are decorator arguments, __call__() is only called
        once, as part of the decoration process! You can only give
        it a single argument, which is the function object.
        """
        cmd.register(self._spec, func)
        return func

    @classmethod
    def register(cls, spec, func, prepend=False):
        if prepend:
            cls._specs.insert(0, (spec, func))
        else:
            cls._specs.append((spec, func))

    @classmethod
    def dispatch(cls, arguments, **kwargs):
        """Dispatch arguments parsed by docopt to the cmd with matching spec.

        :param arguments:
        :param kwargs:
        :return: exit_code
        """
        # first match wins
        # spec: all '-' elements must match, all others are False;
        #       '<sth>' elements are converted to call args on order of
        #       appearance
        #
        # kwargs are provided to dispatch call and used in func call
        for spec, func in cls._specs:
            # if command and arguments.get(command) and match(args):
            args = []  # specified args in order of appearance
            options = list(filter(lambda k: k.startswith('-') and
                                       (arguments[k] or k in spec),
                             arguments.keys()))
            cmds = list(filter(lambda k: not (k.startswith('-') or
                                         k.startswith('<')) and arguments[k],
                          arguments.keys()))
            args_spec = list(filter(lambda k: k.startswith('<'), spec))
            cmd_spec = list(filter(lambda k: not (k.startswith('-') or
                                             k.startswith('<')), spec))
            for element in spec:
                if element.startswith('-'):
                    # element is an option
                    if element in options:
                        args.append(arguments.get(element, False))
                        options.remove(element)
                elif element.startswith('<') and \
                        not arguments.get(element) is False:
                    # element is an argument
                    args.append(arguments.get(element))
                    if element in args_spec:
                        args_spec.remove(element)
                else:
                    # element is a command
                    if element in cmds and element in cmd_spec:
                        cmds.remove(element)
                        cmd_spec.remove(element)

            if options:
                continue  # not all options have been matched
            if cmds:
                continue  # not all cmds from command line have been matched
            if args_spec:
                continue  # not all args from spec have been provided
            if cmd_spec:
                continue  # not all cmds from spec have been provided
            # all options and cmds matched : call the cmd
            # TODO leave out all args to deal with "empty" signature
            exit_code = func(*args, **kwargs)
            return exit_code
        # no matching spec found
        raise Exception('No implementation for spec: %s' % arguments)


def get_command(arguments):
    """Utility function to extract command from docopt arguments.

    :param arguments:
    :return: command
    """
    cmds = list(filter(lambda k: not (k.startswith('-') or
                                 k.startswith('<')) and arguments[k],
                  arguments.keys()))
    if len(cmds) != 1:
        raise Exception('invalid command line!')
    return cmds[0]
