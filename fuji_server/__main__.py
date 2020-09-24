#!/usr/bin/env python3

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
import argparse
import configparser
import logging
import os
from logging.config import fileConfig
import connexion
from werkzeug.middleware.proxy_fix import ProxyFix

from fuji_server import encoder
from fuji_server.helper.preprocessor import Preprocessor
import fuji_server.controllers.authorization_controller as authen

def main():
    logging.getLogger('connexion.operation').setLevel('INFO')
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    YAML_DIR = config['SERVICE']['yaml_directory']
    METRIC_YAML = config['SERVICE']['metrics_yaml']
    METRIC_YML_PATH = os.path.join(ROOT_DIR, YAML_DIR, METRIC_YAML)
    SPDX_URL = config['EXTERNAL']['spdx_license_github']
    DATACITE_API_REPO = config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = config['EXTERNAL']['re3data_api']
    METADATACATALOG_API = config['EXTERNAL']['metadata_catalog']
    LOV_API = config['EXTERNAL']['lov_api']
    LOD_CLOUDNET = config['EXTERNAL']['lod_cloudnet']
    #BIOPORTAL_REST = config['EXTERNAL']['bioportal_rest']
    #BIOPORTAL_APIKEY = config['EXTERNAL']['bioportal_apikey']
    data_files_limit = int(config['SERVICE']['data_files_limit'])
    metric_specification = config['SERVICE']['metric_specification']

    #TODO further implementation on authentication needed
    usr = config['USER']['usr']
    pwd = config['USER']['pwd']
    authen.service_username = usr
    authen.service_password = pwd

    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH, data_files_limit, metric_specification)
    logger.info('Total metrics defined: {}'.format(preproc.get_total_metrics()))

    isDebug = config.getboolean('SERVICE', 'debug_mode')
    preproc.retrieve_licenses(SPDX_URL, isDebug)
    preproc.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    preproc.retrieve_metadata_standards(METADATACATALOG_API, isDebug)
    #preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, bioportal_api=BIOPORTAL_REST, bioportal_key=BIOPORTAL_APIKEY, isDebugMode=False)
    preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)
    preproc.retrieve_default_namespaces()

    logger.info('Total SPDX licenses : {}'.format(preproc.get_total_licenses()))
    logger.info('Total re3repositories found from datacite api : {}'.format(len(preproc.getRE3repositories())))
    logger.info('Total subjects area of imported metadata standards : {}'.format(len(preproc.metadata_standards)))
    logger.info('Total LD vocabs imported : {}'.format(len(preproc.getLinkedVocabs())))
    logger.info('Total default namespaces specified : {}'.format(len(preproc.getDefaultNamespaces())))

    #you can also use Tornado or gevent as the HTTP server, to do so set server to tornado or gevent
    app = connexion.FlaskApp(__name__, specification_dir=YAML_DIR)
    API_YAML = os.path.join(ROOT_DIR, YAML_DIR, config['SERVICE']['swagger_yaml'])
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(API_YAML, arguments={'title': 'F-UJI : FAIRsFAIR Research Data Object Assessment Service'}, validate_responses=True)
    app.app.wsgi_app = ProxyFix(app.app.wsgi_app)
    app.run(host=config['SERVICE']['service_host'], port=int(config['SERVICE']['service_port']))

if __name__ == '__main__':
    global config
    my_path = os.path.abspath(os.path.dirname(__file__))
    parser = argparse.ArgumentParser()
    # add a new command line option, call it '-c' and set its destination to 'config_file'
    parser.add_argument("-c", "--config", required=True, help="Path to server.ini config file")
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read(args.config)
    log_configfile = os.path.join(my_path,config['SERVICE']['log_config'])
    log_dir = config['SERVICE']['logdir']
    log_directory = os.path.join(my_path, log_dir)
    log_file_path = os.path.join(log_directory, 'fuji.log')
    if not os.path.exists(log_directory):
        os.makedirs(log_directory, exist_ok=True)
    fileConfig(log_configfile, defaults={'logfilename': log_file_path.replace("\\", "/")})
    logger = logging.getLogger()  # use this form to initialize the root logger
    main()