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
    ROOT_DIR = Path(__file__).parent
    SPEC_DIR = ROOT_DIR / config["SERVICE"]["yaml_directory"]
    API_YAML = SPEC_DIR / config["SERVICE"]["openapi_yaml"]

    jsonifier = Jsonifier(json, cls=encoder.CustomJSONEncoder)
    app = connexion.App(__name__, specification_dir=SPEC_DIR, jsonifier=jsonifier)
    app.add_api(API_YAML, validate_responses=True, jsonifier=jsonifier)
    app.app.wsgi_app = ProxyFix(app.app.wsgi_app, x_for=1, x_host=1)

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

    return app
