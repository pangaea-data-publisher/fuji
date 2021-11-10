# -*- coding: utf-8 -*-

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
import os
import connexion
from flask_cors import CORS
from fuji_server import encoder
from pathlib import Path
from werkzeug.middleware.proxy_fix import ProxyFix


def create_fuji_app(config):
    #you can also use Tornado or gevent as the HTTP server, to do so set server to tornado or gevent
    ROOT_DIR = main_dir = Path(__file__).parent.parent#os.path.dirname(os.path.abspath(__file__))
    YAML_DIR = config['SERVICE']['yaml_directory']


    auth_enabled = config.getboolean('USER', 'auth_enabled')

    app = connexion.FlaskApp(__name__, specification_dir=YAML_DIR)
    API_YAML = os.path.join(ROOT_DIR, YAML_DIR, config['SERVICE']['swagger_yaml'])
    app.app.json_encoder = encoder.JSONEncoder
    api_title = 'F-UJI : FAIRsFAIR Research Data Object Assessment Service'
    if auth_enabled:
        api_args = {'title': api_title, 'security': [{'basicAuth': []}]}
    else:
        api_args = {'title': api_title}

    app.add_api(API_YAML, arguments=api_args, validate_responses=True)
    app.app.wsgi_app = ProxyFix(app.app.wsgi_app, x_for=1, x_host=1)
    if os.getenv('ENABLE_CORS', 'False').lower() == 'true':
        CORS(app.app)
    return app