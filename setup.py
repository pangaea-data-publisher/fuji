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
    license='MIT License',
    description="FUJI (FAIRsFAIR Data Assessment Service)",
    author="Anusuriya Devaraju",
    author_email="adevaraju@marum.de",
    url="http://www.anusuriya.com",
    keywords=["Swagger", "PANGAEA", "FAIRsFAIR", "FAIR Principles", "Data Object Assessment"],
    install_requires=REQUIRES,
    packages=find_packages(exclude=["tests", "logs"]),
    package_data={'': ['yaml/*.yaml','config/*']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['fuji_server=fuji_server.__main__:main']},
    long_description="A service to evaluate FAIR data objects based on FAIRsFAIR Metrics"
)