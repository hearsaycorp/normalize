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

install_requires=[
    'richenum>=1.0.0',
    'six',
    'future'
]

tests_require=[
    'pytest>=4.6.5',
    'more-itertools>=5.0.0',
    'unittest2',
    'pathlib2',
    'configparser'
]

setup(
    author='Hearsay Social',
    author_email='opensource@hearsaysocial.com',
    description="Declarative Python meta-model system and visitor utilities",
    license='MIT',
    long_description=long_description,
    name='normalize',
    packages=find_packages(),
    install_requires=install_requires,
    tests_require=tests_require,
    test_suite="tests",
    version='2.0.3',
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
