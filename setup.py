from setuptools import find_packages, setup


setup(
    author='Hearsay Labs, Inc',
    author_email='svilain@hearsaylabs.com',
    description="Declarative Python meta-model system and visitor utilities",
    license='MIT',
    long_description="""
This module lets you declare classes and object properties, and then
get support for marshaling to and from JSON data model, as well as the
ability to retrieve a list of differences between two parsed data
structures, and refer to fields within a structure using a 'selector'.
""",
    name='normalize',
    packages=find_packages(),
    requires=['richenum (>=1.0.0)'],
    test_suite="run_tests",
    version='0.4.6',
    url="http://hearsaycorp.github.io/normalize",
)
