#!/usr/bin/env python

from setuptools import find_packages, setup


try:
    with open("README.rst", "ro") as readme:
        lines = []
        for line in readme:
            lines.append(line)
            if "...and much more" in line:
                break
        long_description = "".join(lines)
except:
    long_description = """
This module lets you declare classes and object properties, and then
get support for marshaling to and from JSON data.  You can also compare
objects to see if they have changed in meaningful ways.
"""


setup(
    author='Hearsay Social',
    author_email='opensource@hearsaysocial.com',
    description="Declarative Python meta-model system and visitor utilities",
    license='MIT',
    long_description=long_description,
    name='normalize',
    packages=find_packages(),
    install_requires=('richenum>=1.0.0',),
    tests_require=('nose', 'unittest2'),
    test_suite="run_tests",
    version='1.0.2',
    url="http://hearsaycorp.github.io/normalize",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
