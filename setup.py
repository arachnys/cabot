from distutils.core import setup
setup(
  name = 'mypackage',
  packages = ['mypackage'], # this must be the same as the name above
  version = '0.1',
  description = 'my description',
  author = 'Alejandro Esquiva',
  author_email = 'alejandro@geekytheory.com',
  url = 'https://github.com/{user_name}/{repo}', # use the URL to the github repo
  download_url = 'https://github.com/{user_name}/{repo}/tarball/0.1',
  keywords = ['testing', 'logging', 'example'],
  classifiers = [],
)
