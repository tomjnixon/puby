#!/usr/bin/env python

from setuptools import setup

setup(
    name='puby',
    version='0.1',
    description='Embed a ruby interpreter in python.',
    author='Tom Nixon',
    url='http://github.com/tomjnixon/puby',
    install_requires=['cffi>=0.6'],
    package_dir = {'puby': 'src'},
    packages=['puby'])

