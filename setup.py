# -*- coding: utf-8 -*-
"""
setup: usage: pip install -e .[graphs]
"""

from setuptools import setup, find_packages
import io  # needed to have `open` with encoding option

# read the contents of your README file, needed for display on pypi and other indexers
from os import path

this_directory = path.abspath(path.dirname(__file__))
with io.open(path.join(this_directory, 'README.md'), encoding='utf8') as f:
    long_description = f.read()

setup(
    name='fuji_server',
    version='1.0.0',
    description='FUJI (FAIRsFAIR Data Objects Assessment Service), A service to evaluate FAIR data objects based on FAIRsFAIR Metrics',
    # add long_description from readme.md:
    long_description = long_description, # add contents of README.md
    long_description_content_type ='text/markdown',  # This is important to activate markdown!
    url='https://github.com/pangaea-data-publisher/fuji',
    author="See AUTHORS file",
    author_email="rhuber@marum.de",
    maintainer='Robert Huber',
    maintainer_email="rhuber@marum.de",
    license='MIT License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    keywords=["PANGAEA", "FAIRsFAIR", "FAIR Principles", "Data Object Assessment","Swagger",'FAIR', 'Research Data', 'FAIR data', 'Metadata harvesting'],
    packages=find_packages(exclude=['tests*', "logs"]),
    package_data={'': ['data/*.*','yaml/*.yaml','config/*']},
    include_package_data=True,
    install_requires=[
        'requests',
        'pyyaml',
        'connexion[swagger-ui]',
        'extruct',
        'rdflib',
        'idutils',
        'lxml>=4.6.3',
        'Levenshtein',
        'sparqlwrapper',
        'jmespath',
        'six',
        'connexion',
        'tika',
        'configparser',
        'werkzeug',
        'rapidfuzz',
        'setuptools',
        'urlextract',
        'feedparser',
        'beautifulsoup4',
        'hashid',
        'pandas',
        'tldextract'
    ],
    extras_require={
        'pre-commit': [
            'pre-commit>=2.6.0',
            'yapf>=0.30.0',
            'pylint>=2.5.2',
            'pytest>=4.3.1'
        ],
        'docs': [
            'Sphinx',
            'docutils',
            'sphinx_rtd_theme'
        ],
        'testing': [
            'pytest>=4.3.1',
            'pytest-cov',
            'pytest-xprocess'
        ],
        'bokeh-plots': [
            'bokeh' 
        ]
    },
    entry_points={
        'console_scripts': ['fuji_server=fuji_server.__main__:main']},
)