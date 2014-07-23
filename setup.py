from setuptools import find_packages, setup


setup(
    author='Hearsay Labs, Inc',
    author_email='svilain@hearsaylabs.com',
    description="Declarative Python meta-model system and visitor utilities",
    license='MIT',
    long_description="""
This module lets you declare classes and object properties, and then
get support for marshaling to and from JSON data.  You can also compare
objects to see if they have changed in meaningful ways.
""",
    name='normalize',
    packages=find_packages(),
    install_requires=('richenum>=1.0.0',),
    test_suite="run_tests",
    version='0.4.7',
    url="http://hearsaycorp.github.io/normalize",
)
