# -*- coding: utf-8 -*-
"""
A collection of tests to test the reponses of a Fask tesk fuji client,
i.e. if the app is working and there are no swagger problems.
"""

def test_ui(fujiclient):
    """Basic smoke test to see if app is buildable"""
    response = fujiclient.get('/fuji/api/v1/ui/')
    print(response.data)
    assert response.status_code == 200


def test_ui_break(fujiclient):
    """Basic test if a path not in the UI gives a 404"""
    response = fujiclient.get('/fuji/500api/v1/ui/')
    print(response.data)
    assert response.status_code == 404


def test_get_metrics(fujiclient):
    """Test if a client get returns the metric"""
    response = fujiclient.get('/fuji/api/v1/metrics',
                              headers={
                                  'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                                  'accept': 'application/json'
                              })
    print(response)
    assert response.status_code == 200
    result = response.json
    assert result != {}

'''
from swagger_tester import swagger_test

def test_swagger_api(swagger_yaml):
    swagger_test(swagger_yaml)


def test_swagger_api2(app_url):
    swagger_test(app_url=app_url)
'''
'''
def test_login_logout(client):
    """Make sure login and logout works."""

    username = flaskr.app.config["USERNAME"]
    password = flaskr.app.config["PASSWORD"]

    rv = login(client, username, password)
    assert b'You were logged in' in rv.data

    rv = logout(client)
    assert b'You were logged out' in rv.data

    rv = login(client, f"{username}x", password)
    assert b'Invalid username' in rv.data

    rv = login(client, username, f'{password}x')
    assert b'Invalid password' in rv.data
'''
