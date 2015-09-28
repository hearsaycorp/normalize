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
    author='Hearsay Labs, Inc',
    author_email='svilain@hearsaylabs.com',
    description="Declarative Python meta-model system and visitor utilities",
    license='MIT',
    long_description=long_description,
    name='normalize',
    packages=find_packages(),
    install_requires=('richenum>=1.0.0',),
    test_suite="run_tests",
    version='1.0.0',
    url="http://hearsaycorp.github.io/normalize",
)
