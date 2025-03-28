#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import argparse
import configparser
import logging
import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from fuji_server.app import create_app
from fuji_server.helper.preprocessor import Preprocessor


def main():
    logging.getLogger("connexion.operation").setLevel("INFO")
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    YAML_DIR = config["SERVICE"]["yaml_directory"]
    # METRIC_YAML = config['SERVICE']['metrics_yaml']
    # YAML_DIR = os.path.join(my_path, config['SERVICE']['yaml_directory'])
    METRIC_YML_PATH = os.path.join(ROOT_DIR, YAML_DIR)
    print("YAML PATH", METRIC_YML_PATH)
    """SPDX_URL = config['EXTERNAL']['spdx_license_github']
    DATACITE_API_REPO = config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = config['EXTERNAL']['re3data_api']
    METADATACATALOG_API = config['EXTERNAL']['metadata_catalog']"""
    # BIOPORTAL_REST = config['EXTERNAL']['bioportal_rest']
    # BIOPORTAL_APIKEY = config['EXTERNAL']['bioportal_apikey']
    data_files_limit = int(config["SERVICE"]["data_files_limit"])

    preproc = Preprocessor()
    # preproc.retrieve_metrics_yaml(METRIC_YML_PATH,  metric_specification)
    preproc.set_data_files_limit(data_files_limit)
    preproc.set_metric_yaml_path(METRIC_YML_PATH)
    # logger.info('Total metrics defined: {}'.format(preproc.get_total_metrics()))

    isDebug = config.getboolean("SERVICE", "debug_mode")
    preproc.retrieve_licenses(isDebug)
    preproc.retrieve_datacite_re3repos()

    preproc.retrieve_metadata_standards()
    # preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, bioportal_api=BIOPORTAL_REST, bioportal_key=BIOPORTAL_APIKEY, isDebugMode=False)
    # preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)
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
    my_path = os.path.abspath(os.path.dirname(__file__))
    parser = argparse.ArgumentParser()
    # add a new command line option, call it '-c' and set its destination to 'config_file'
    parser.add_argument("-c", "--config", required=True, help="Path to server.ini config file")
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read(args.config)
    log_configfile = os.path.join(my_path, config["SERVICE"]["log_config"])
    log_dir = config["SERVICE"]["logdir"]
    log_directory = os.path.join(my_path, log_dir)
    log_file_path = os.path.join(log_directory, "fuji.log")

    if not os.path.exists(log_directory):
        os.makedirs(log_directory, exist_ok=True)
    # fileConfig(log_configfile, defaults={'logfilename': log_file_path.replace("\\", "/")})
    logger = logging.getLogger()  # use this form to initialize the root logger
    main()
