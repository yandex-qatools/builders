#!/usr/bin/env python

from builders import info

import setuptools


setuptools.setup(
    name=info.__package_name__,
    version=info.__version__,
    description="Builders for abstract models",
    author="Ivan Kalinin",
    author_email="pupssman@yandex-team.ru",
    url="http://wiki.yandex-team.ru/",
    packages=["builders"],
    long_description="""This module provides abstract tree building capability""",
)
