import os
from distutils.util import strtobool


def force_bool(val):
    if val == True or val  == False:
        return strtobool(str(val))
    else:
        return False

def environ_get_list(names, default=None):

    for name in names:
    
        if name in os.environ:

            return os.environ[name]
    return default
