#!/usr/bin/env python

from builders import info

import setuptools


setuptools.setup(
    name=info.__package_name__,
    version=info.__version__,
    license='Apache License, Version 2.0',
    author="Ivan Kalinin",
    author_email="pupssman@yandex-team.ru",
    url="http://github.com/yandex-qatools/builders",
    packages=["builders"],
    description="Lightweight test data generation framework",
    long_description=open('README.rst').read(),
    classifiers=[
                'Development Status :: 5 - Production/Stable',
                'Environment :: Console',
                'Intended Audience :: Developers',
                'License :: OSI Approved :: Apache Software License',
                'Operating System :: OS Independent',
                'Programming Language :: Python',
                'Topic :: Software Development',
                'Topic :: Software Development :: Quality Assurance',
                'Topic :: Software Development :: Testing'],
)
