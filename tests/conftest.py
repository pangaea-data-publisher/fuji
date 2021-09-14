# -*- coding: utf-8 -*-
"""
Configurations and fixtures for fuji_server tests
"""
import pytest
from pprint import pprint

pytest_plugins = ()

# use pytest-xprocess ? https://pytest-xprocess.readthedocs.io/en/latest/

def mock_fuji_server_instance():
    pass


@pytest.fixture(scope='session', autouse=True)
def session_fixture():

    yield  #Now all tests run
