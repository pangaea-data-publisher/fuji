# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

"""
Controller generated to handled auth operation described at:
https://connexion.readthedocs.io/en/latest/security.html
"""

import fuji_server.config.users as fuji_user


def checkUser(
    username: str, password: str, required_scopes=None, user_dict: dict = fuji_user.fuji_users
) -> dict | None:
    """Function to check if a given user name and password are in the allowed user dict of fuji

    This is not save.
    """
    # service_username = 'marvel'
    # service_password = 'wonderwoman'
    if username in user_dict:
        if password == user_dict.get(username):
            return {"username": username, "password": user_dict.get(username)}
        else:
            return None
    else:
        return None
