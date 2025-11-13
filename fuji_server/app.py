# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import json
import os
from pathlib import Path

import connexion
from connexion.jsonifier import Jsonifier
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix

from fuji_server import encoder


def create_app(config):
    """
    Function which initializes the FUJI connexion flask app and returns it
    """
    # you can also use Tornado or gevent as the HTTP server, to do so set server to tornado or gevent
    ROOT_DIR = Path(__file__).parent
    YAML_DIR = config["SERVICE"]["yaml_directory"]
    API_YAML = ROOT_DIR / YAML_DIR / config["SERVICE"]["openapi_yaml"]

    myjsonifier = Jsonifier(json, cls=encoder.CustomJSONEncoder)
    app = connexion.App(__name__, specification_dir=YAML_DIR, jsonifier=myjsonifier)

    # Ref: https://connexion.readthedocs.io/en/latest/cookbook.html#cors
    if os.getenv("ENABLE_CORS", "False").lower() == "true":
        app.add_middleware(
            CORSMiddleware,
            position=MiddlewarePosition.BEFORE_EXCEPTION,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_api(API_YAML, validate_responses=True, jsonifier=myjsonifier)
    app.app.wsgi_app = ProxyFix(app.app.wsgi_app, x_for=1, x_host=1)
    return app
