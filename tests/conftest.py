# -*- coding: utf-8 -*-
"""
Configurations and fixtures for fuji_server tests
"""
import os
import pytest
import configparser

from pprint import pprint
#from fuji_server import main
import connexion
from pathlib import Path
from flask.testing import FlaskClient
from fuji_server.app.fuji_app import create_fuji_app

pytest_plugins = ()

THIS_PATH = Path(__file__).parent
TEST_CONFIG_FILE_PATH = os.path.join(THIS_PATH, 'test_server.ini')
config = configparser.ConfigParser()
config.read(TEST_CONFIG_FILE_PATH)
flask_app = create_fuji_app(config)
flask_app.testing = True

@pytest.fixture(scope='session')
def fujiclient():
    with flask_app.app.test_client() as test_client:
        #login(test_client, "username", "password")
        yield test_client


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
