#!/usr/bin/env python

from builders import info

import setuptools


setuptools.setup(
    name=info.__package_name__,
    version=info.__version__,
    license="Apache",
    author="Ivan Kalinin",
    author_email="pupssman@yandex-team.ru",
    url="http://github.com/yandex-qatools/builders",
    packages=["builders"],
    description="Lightweight test data generation framework",
    long_description=open('doc/tutorial.rst').read(),
)
