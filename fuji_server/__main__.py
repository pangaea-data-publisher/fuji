#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import argparse
import configparser
import logging
import logging.config
from pathlib import Path

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from fuji_server.app import create_app
from fuji_server.helper.preprocessor import Preprocessor

ROOT_DIR = Path(__file__).parent


def main(config):
    METRIC_YML_PATH = ROOT_DIR / config["SERVICE"]["yaml_directory"]
    logger.info("YAML PATH: %s", METRIC_YML_PATH)

    LOV_API = config["EXTERNAL"]["lov_api"]
    LOD_CLOUDNET = config["EXTERNAL"]["lod_cloudnet"]

    data_files_limit = int(config["SERVICE"]["data_files_limit"])

    preproc = Preprocessor()
    preproc.set_data_files_limit(data_files_limit)
    preproc.set_metric_yaml_path(METRIC_YML_PATH)
    isDebug = config.getboolean("SERVICE", "debug_mode")
    preproc.retrieve_licenses(isDebug)
    preproc.retrieve_datacite_re3repos()
    preproc.retrieve_metadata_standards()
    preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)
    preproc.set_remote_log_info(config["SERVICE"].get("remote_log_host"), config["SERVICE"].get("remote_log_path"))
    preproc.set_max_content_size(config["SERVICE"]["max_content_size"])

    logger.info("Total SPDX licenses: %s", preproc.get_total_licenses())
    logger.info("Total re3repositories found from datacite api: %s", len(preproc.getRE3repositories()))
    logger.info("Total subjects area of imported metadata standards: %s", len(preproc.metadata_standards))
    logger.info("Total LD vocabs imported: %s", len(preproc.getLinkedVocabs()))
    logger.info("Total default namespaces specified: %s", len(preproc.getDefaultNamespaces()))

    app = create_app(config)
    Limiter(get_remote_address, app=app.app, default_limits=[str(config["SERVICE"]["rate_limit"])])
    # built in uvicorn ASGI
    app.run(host=config["SERVICE"]["service_host"], port=int(config["SERVICE"]["service_port"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # add a new command line option, call it '-c' and set its destination to 'config_file'
    parser.add_argument("-c", "--config", required=True, help="Path to server.ini config file")
    args = parser.parse_args()

    # load application config
    config = configparser.ConfigParser()
    config.read(args.config)

    log_configfile = ROOT_DIR / config["SERVICE"]["log_config"]
    log_directory = ROOT_DIR / config["SERVICE"]["logdir"]
    log_file_path = log_directory / "fuji.log"

    if not log_directory.exists():
        log_directory.mkdir(exist_ok=True)

    # load logging config
    logging_config = configparser.ConfigParser()
    logging_config.read(log_configfile)

    logging.config.fileConfig(log_configfile, defaults={"logfilename": log_file_path})
    logging.getLogger("connexion").setLevel("INFO")

    logger = logging.getLogger(__name__)

    main(config)
