try:
    import pkg_resources
    version = pkg_resources.require("cabot3")[0].version
except Exception(ImportError):
    version = 'unknown'
