# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import json
import os
from pathlib import Path

import connexion
from connexion.jsonifier import Jsonifier
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
    myjsonifier = Jsonifier(json, cls=encoder.CustomJSONEncoder)
    # app = connexion.FlaskApp(__name__, specification_dir=YAML_DIR, jsonifier=encoder.CustomJsonifier)
    app = connexion.App(__name__, specification_dir=YAML_DIR, jsonifier=myjsonifier)

    API_YAML = ROOT_DIR.joinpath(YAML_DIR, config["SERVICE"]["openapi_yaml"])

    app.add_api(API_YAML, validate_responses=True, jsonifier=myjsonifier)

    app.app.wsgi_app = ProxyFix(app.app.wsgi_app, x_for=1, x_host=1)
    if os.getenv("ENABLE_CORS", "False").lower() == "true":
        CORS(app.app)

    return app
