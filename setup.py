#!/usr/bin/env python
import os
from setuptools import setup, find_packages
from os import environ as env
import subprocess

from pip.req import parse_requirements

requirements = [str(req.req) for req in parse_requirements('requirements.txt', session=False)]
requirements_plugins = [str(req.req) for req in parse_requirements('requirements-plugins.txt', session=False)]

try:
    VERSION = subprocess.check_output(['git', 'describe', '--tags']).strip()
except subprocess.CalledProcessError:
    VERSION = '0.dev'

setup(
    name='cabot',
    version=VERSION,
    description="Self-hosted, easily-deployable monitoring and alerts service"
                " - like a lightweight PagerDuty",
    long_description=open('README.md').read(),
    author="Arachnys",
    author_email='info@arachnys.com',
    url='http://cabotapp.com',
    license='MIT',
    install_requires=requirements + requirements_plugins,
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'cabot = cabot.entrypoint:main',
        ],
    },
    zip_safe=False
)
