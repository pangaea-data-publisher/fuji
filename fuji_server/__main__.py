#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import argparse
import configparser
import logging
import os
from pathlib import Path

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from fuji_server.app import create_app
from fuji_server.helper.preprocessor import Preprocessor


def main():
    logging.getLogger("connexion.operation").setLevel("INFO")
    ROOT_DIR = Path(__file__).parent
    YAML_DIR = config["SERVICE"]["yaml_directory"]
    METRIC_YML_PATH = ROOT_DIR / YAML_DIR
    data_files_limit = int(config["SERVICE"]["data_files_limit"])

    preproc = Preprocessor()
    preproc.set_data_files_limit(data_files_limit)
    preproc.set_metric_yaml_path(METRIC_YML_PATH)

    isDebug = config.getboolean("SERVICE", "debug_mode")
    preproc.retrieve_licenses(isDebug)
    preproc.retrieve_datacite_re3repos()

    preproc.retrieve_metadata_standards()
    preproc.set_remote_log_info(config["SERVICE"].get("remote_log_host"), config["SERVICE"].get("remote_log_path"))
    preproc.set_max_content_size(config["SERVICE"]["max_content_size"])

    logger.info(f"Total SPDX licenses : {preproc.get_total_licenses()}")
    logger.info(f"Total re3repositories found from datacite api : {len(preproc.getRE3repositories())}")
    logger.info(f"Total subjects area of imported metadata standards : {len(preproc.metadata_standards)}")
    logger.info(f"Total LD vocabs imported : {len(preproc.getLinkedVocabs())}")
    logger.info(f"Total default namespaces specified : {len(preproc.getDefaultNamespaces())}")

    app = create_app(config)
    Limiter(get_remote_address, app=app.app, default_limits=[str(config["SERVICE"]["rate_limit"])])
    # built in uvicorn ASGI
    app.run(host=config["SERVICE"]["service_host"], port=int(config["SERVICE"]["service_port"]))


if __name__ == "__main__":
    global config
    ROOT_DIR = Path(__file__).parent

    parser = argparse.ArgumentParser()
    # add a new command line option, call it '-c' and set its destination to 'config_file'
    parser.add_argument("-c", "--config", required=True, help="Path to server.ini config file")
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read(args.config)
    log_configfile = ROOT_DIR / config["SERVICE"]["log_config"]
    log_dir = config["SERVICE"]["logdir"]
    log_directory = ROOT_DIR / log_dir
    log_file_path = log_directory / "fuji.log"

    if not os.path.exists(log_directory):
        log_directory.mkdir(exist_ok=True)
    logger = logging.getLogger()  # use this form to initialize the root logger
    main()
