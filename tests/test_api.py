# -*- coding: utf-8 -*-


def test_ui(fujiclient):
    response = fujiclient.get('/fuji/api/v1/ui/')
    print(response.data)
    assert response.status_code == 200


def test_ui_break(fujiclient):
    response = fujiclient.get('/fuji/500api/v1/ui/')
    print(response.data)
    assert response.status_code == 404


def test_get_metrics(fujiclient):  #, login_client):
    #print(url_for('/fuji/api/v1/metrics'))
    #response = login_client(fujiclient)
    #assert response.status_code == 200
    response = fujiclient.get('/fuji/api/v1/metrics',
                              headers={
                                  'Authorization': 'Basic dXNlcm5hbWU6cGFzc3dvcmQ=',
                                  'accept': 'application/json'
                              })
    #, data=dict(
    #    username="username",
    #    password="password"
    #), follow_redirects=True)#  Authorization= "Basic dXNlcm5hbWU6cGFzc3dvcmQ=") # accept="application/json",
    print(response.json)
    print(response)
    assert response.status_code == 200


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
