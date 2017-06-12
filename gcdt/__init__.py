__version__ = '0.1.396'

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
