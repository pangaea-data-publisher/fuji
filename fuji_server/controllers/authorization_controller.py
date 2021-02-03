from typing import List
"""
controller generated to handled auth operation described at:
https://connexion.readthedocs.io/en/latest/security.html
"""

service_username = None
service_password = None

def checkUser(username, password, required_scopes=None):
    if username == service_username and password == service_password:
        return {'username':service_username, 'password': service_password}
    else:
        return None


