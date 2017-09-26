# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function


class GcdtError(Exception):
    """
    The base exception class for gcdt exceptions.

    :param msg: The descriptive message associated with the error.
    """
    msg = 'An unspecified error occurred'

    def __init__(self, *args, **kwargs):
        #msg = self.fmt.format(**kwargs)
        if not args:
            args = [self.msg]
        Exception.__init__(self, *args, **kwargs)


class GracefulExit(Exception):
    """
    transport the signal information
    note: if you capture Exception you have to deal with this case, too
    """
    pass


class InvalidCredentialsError(GcdtError):
    """
    Unusable credentials
    """
    msg = 'Your credentials have expired... Please renew and try again!'
