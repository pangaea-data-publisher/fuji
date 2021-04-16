from typing import List
"""
controller generated to handled auth operation described at:
https://connexion.readthedocs.io/en/latest/security.html
"""

import fuji_server.config.users as fuji_user

def checkUser(username, password, required_scopes=None, user_dict = fuji_user.fuji_users):
    #service_username = 'marvel'
    #service_password = 'wonderwoman'
    if username in user_dict:
        if password == user_dict.get(username):
            return {'username':username, 'password': user_dict.get(username)}
        else:
            return None
    else:
        return None


