import os

def environ_get_list(names, default=None):
    for name in names:
        if name in os.environ:
            return os.environ[name]
    return default
