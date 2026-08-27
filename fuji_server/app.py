# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import json
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path

import connexion
from connexion.jsonifier import Jsonifier

import yaml
from fuji_server.helper.browser_manager import BrowserManager


class FujiJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


@asynccontextmanager
async def lifespan(app):
    # Startup
    await BrowserManager.init_browser()
    try:
        yield
    finally:
        # Shutdown
        await BrowserManager.stop_browser()


def create_app(config):
    myjsonifier = Jsonifier(json, cls=FujiJSONEncoder)

    ROOT_DIR = Path(__file__).parent
    yaml_dir = ROOT_DIR / config["SERVICE"]["yaml_directory"]
    api_file = yaml_dir / config["SERVICE"]["openapi_yaml"]

    print("YAML absolute path:", api_file)
    print("YAML exists?", api_file.exists())

    with open(api_file, encoding="utf-8") as f:
        openapi_spec = yaml.safe_load(f)

    # 👇 lifespan registered HERE
    app = connexion.AsyncApp(__name__, jsonifier=myjsonifier, lifespan=lifespan)

    app.add_api(specification=openapi_spec, validate_responses=False)

    return app
