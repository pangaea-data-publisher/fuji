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
from pathlib import Path

import connexion
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from fuji_server import encoder


def create_app(config):
    """
    Function which initializes the FUJI connexion flask app and returns it
    """
    # you can also use Tornado or gevent as the HTTP server, to do so set server to tornado or gevent
    ROOT_DIR = Path(__file__).parent
    YAML_DIR = config["SERVICE"]["yaml_directory"]

    app = connexion.FlaskApp(__name__, specification_dir=YAML_DIR)
    API_YAML = ROOT_DIR.joinpath(YAML_DIR, config["SERVICE"]["swagger_yaml"])
    app.app.json_encoder = encoder.JSONEncoder

    app.add_api(API_YAML, validate_responses=True)
    app.app.wsgi_app = ProxyFix(app.app.wsgi_app, x_for=1, x_host=1)
    if os.getenv("ENABLE_CORS", "False").lower() == "true":
        CORS(app.app)

    return app
