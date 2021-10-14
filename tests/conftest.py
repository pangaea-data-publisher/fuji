# -*- coding: utf-8 -*-
"""
Configurations and fixtures for fuji_server tests
"""
import pytest
from pprint import pprint
#from fuji_server import main
import connexion
from flask.testing import FlaskClient

pytest_plugins = ()

swagger_filepath = '../fuji_server/yaml/swagger.yaml'
flask_app = connexion.FlaskApp(__name__)
flask_app.add_api(swagger_filepath)
flask_app.testing = True


@pytest.fixture(scope='session')
def fujiclient():
    with flask_app.app.test_client() as test_client:
        #login(test_client, "username", "password")
        yield test_client

