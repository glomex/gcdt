# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function


class GcdtError(Exception):
    """
    The base exception class for gcdt exceptions.

    :ivar msg: The descriptive message associated with the error.
    """
    fmt = 'An unspecified error occurred'

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs


class GracefulExit(Exception):
    """
    transport the signal information
    note: if you capture Exception you have to deal with this case, too
    """
    pass