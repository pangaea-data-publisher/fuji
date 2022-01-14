# -*- coding: utf-8 -*-
################################################################################
# MIT License
#
# Copyright (c) 2020 PANGAEA (https://www.pangaea.de/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
################################################################################
"""
Controller generated to handled auth operation described at:
https://connexion.readthedocs.io/en/latest/security.html
"""
from typing import Optional
import fuji_server.config.users as fuji_user


def checkUser(username: str,
              password: str,
              required_scopes=None,
              user_dict: dict = fuji_user.fuji_users) -> Optional[dict]:
    """Function to check if a given user name and password are in the allowed user dict of fuji

    This is not save.
    """
    #service_username = 'marvel'
    #service_password = 'wonderwoman'
    print('check user')
    if username in user_dict:
        if password == user_dict.get(username):
            return {'username': username, 'password': user_dict.get(username)}
        else:
            return None
    else:
        return None
