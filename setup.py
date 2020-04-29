# coding: utf-8

import sys
from setuptools import setup, find_packages

NAME = "fuji_server"
VERSION = "1.0.0"
# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = ["connexion"]

setup(
    name=NAME,
    version=VERSION,
    description="FUJI (FAIRsFAIR Data Assessment Service)",
    author_email="adevaraju@marum.de",
    url="",
    keywords=["Swagger", "PANGAEA", "FAIRsFAIR", "FAIR Principles", "Data Object Assessment"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['yaml/swagger.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['fuji_server=fuji_server.app:main']},
    long_description="""\
    Evaluate Data Objects Based on FAIRsFAIR Metrics
    """
)
