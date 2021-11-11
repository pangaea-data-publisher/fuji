# -*- coding: utf-8 -*-
"""
Configurations and fixtures for fuji_server tests
"""
import os
import pytest
import configparser

from pprint import pprint
#from fuji_server import main
from pathlib import Path
from fuji_server.app.fuji_app import create_fuji_app
from fuji_server.helper.preprocessor import  Preprocessor

pytest_plugins = ()

THIS_PATH = Path(__file__).parent
TEST_CONFIG_FILE_PATH = os.path.join(THIS_PATH, 'test_server.ini')
config_fuji = configparser.ConfigParser()
config_fuji.read(TEST_CONFIG_FILE_PATH)
flask_app = create_fuji_app(config_fuji)
flask_app.testing = True

##### Add some markers to pytest to group tests
# control skipping test on command line options, for test collection
# https://docs.pytest.org/en/stable/example/simple.html?highlight=pytest_configure

def pytest_configure(config):
    """
    Here you can add things by a pytest config, could be also part of a separate file
    So far we add some markers here to be able to execute a certain group of tests
    We make them all lowercaps as convention
    """
    config.addinivalue_line("markers", "manual: tests which should be trickered manual only")
    config.addinivalue_line("markers", "noci: tests which should not run on the CI")



@pytest.fixture(scope='session')
def fujiclient():
    """Fixture providing a fuji flask test_client, for real requests to"""
    with flask_app.app.test_client() as test_client:
        #login(test_client, "username", "password")
        yield test_client


@pytest.fixture(scope='function')
def test_config():
    """Fixture returning the read config object by configparser"""

    return config_fuji


@pytest.fixture(scope='function')
def temp_preprocessor():
    """Fixture which provides a clean temporary Preprocessor (singledton) for a test and tears it down"""
    preproc = Preprocessor()#.copy()
    yield preproc
    # tear down code
    del preproc

'''
class MyResponse(Response):
    """Implements custom deserialization method for response objects."""
    @property
    def json(self):
        return 42

@pytest.fixture(scope="session")
def app():
    app = flask_app
    app.response_class = MyResponse
    return app

'''


@pytest.fixture(scope='function')
def swagger_yaml():
    return swagger_filepath


@pytest.fixture(scope='function')
def app_url():
    return swagger_filepath


def login(fujiclient, username, password):
    return fujiclient.post('/login', data=dict(username=username, password=password), follow_redirects=True)


def logout(client_f):
    return client_f.get('/fuji/api/v1/logout', follow_redirects=True)


@pytest.fixture(scope='function')
def login_client():

    def _login_client(client_f):
        return login(client_f, 'USERNAME', 'PASSWORD')

    return _login_client


# use pytest-xprocess ? https://pytest-xprocess.readthedocs.io/en/latest/


def mock_fuji_server_instance():
    pass


'''
@pytest.fixture(scope='session', autouse=True)
def session_fixture():

    yield  #Now all tests run


@pytest.fixture(scope='module')
def fuji_test_client():
    flask_app = create_app('flask_test.cfg')

    # Flask provides a way to test your application by exposing test Client
    # and handling the context locals for you.
    testing_client = flask_app.test_client()

    # Establish an application context before running the tests.
    ctx = flask_app.app_context()
    ctx.push()

    yield testing_client  # this is where the testing happens!

    ctx.pop()
'''
