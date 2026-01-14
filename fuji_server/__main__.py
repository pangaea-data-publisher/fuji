#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import argparse
import configparser
import logging
import os

import uvicorn

from fuji_server.app import create_app
from fuji_server.helper.preprocessor import Preprocessor

# --- Logging setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main(config):
    logging.getLogger("connexion.operation").setLevel(logging.INFO)

    # --- Paths and preprocessing ---
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    YAML_DIR = config["SERVICE"]["yaml_directory"]
    METRIC_YML_PATH = os.path.join(ROOT_DIR, YAML_DIR)

    preproc = Preprocessor()
    preproc.set_data_files_limit(int(config["SERVICE"]["data_files_limit"]))
    preproc.set_metric_yaml_path(METRIC_YML_PATH)

    is_debug = config.getboolean("SERVICE", "debug_mode")
    preproc.retrieve_licenses(is_debug)
    preproc.retrieve_datacite_re3repos()
    preproc.retrieve_metadata_standards()
    preproc.set_remote_log_info(config["SERVICE"].get("remote_log_host"), config["SERVICE"].get("remote_log_path"))
    preproc.set_max_content_size(config["SERVICE"]["max_content_size"])

    # --- Log preprocessing info ---
    logger.info(f"Total SPDX licenses : {preproc.get_total_licenses()}")
    logger.info(f"Total re3repositories found from datacite api : {len(preproc.getRE3repositories())}")
    logger.info(f"Total subjects area of imported metadata standards : {len(preproc.metadata_standards)}")
    logger.info(f"Total LD vocabs imported : {len(preproc.getLinkedVocabs())}")
    logger.info(f"Total default namespaces specified : {len(preproc.getDefaultNamespaces())}")

    # --- Create Connexion app as WSGI ---
    async_app = create_app(config)

    # --- Set up Flask-Limiter ---
    # Limiter(get_remote_address, app=async_app, default_limits=[str(config["SERVICE"]["rate_limit"])])

    # --- Wrap WSGI app to ASGI for Uvicorn ---
    # asgi_app = WsgiToAsgi(flask_app)

    # --- Run Uvicorn programmatically ---
    uvicorn.run(
        async_app, host=config["SERVICE"]["service_host"], port=int(config["SERVICE"]["service_port"]), log_level="info"
    )


if __name__ == "__main__":
    # --- Parse config ---
    my_path = os.path.abspath(os.path.dirname(__file__))
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="Path to server.ini config file")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)

    # --- Ensure log directory exists ---
    log_dir = os.path.join(my_path, config["SERVICE"]["logdir"])
    os.makedirs(log_dir, exist_ok=True)

    main(config)
