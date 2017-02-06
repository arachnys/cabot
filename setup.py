#!/usr/bin/env python
import os
from setuptools import setup, find_packages
from os import environ as env

requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
with open(requirements_file) as f:
    requirements = [line.rstrip('\n')
                    for line in f
                    if line and not line.startswith('#')]

# pull in active plugins
plugins = env['CABOT_PLUGINS_ENABLED'].split(',') if 'CABOT_PLUGINS_ENABLED' in env else ["cabot_alert_hipchat", "cabot_alert_twilio", "cabot_alert_email"]

setup(
    name='cabot',
    version='0.6.0',
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
