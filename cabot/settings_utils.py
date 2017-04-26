import os
from distutils.util import strtobool


def force_bool(val):
    return strtobool(str(val))


def environ_get_list(names, default=None):
    for name in names:
        if name in os.environ:
            return os.environ[name]
    return default
