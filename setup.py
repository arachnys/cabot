#!/usr/bin/env python
import os
from setuptools import setup, find_packages
from os import environ as env # noqa
import pkg_resources

requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
with open('requirements.txt') as f:
    requirements = list(map(str, pkg_resources.parse_requirements(f)))

# pull in active plugins
with open('requirements-plugins.txt') as f:
    plugins = list(map(str, pkg_resources.parse_requirements(f)))

setup(
    name='cabot',
    version='0.0.2-dev',
    description="Self-hosted, easily-deployable monitoring and alerts service"
                " - like a lightweight PagerDuty",
    long_description=open('README.md').read(),
    author="Arachnys",
    author_email='info@arachnys.com',
    url='http://cabotapp.com',
    license='MIT',
    install_requires=requirements + plugins,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
