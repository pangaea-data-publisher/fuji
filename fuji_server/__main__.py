#!/usr/bin/env python3

import configparser as ConfigParser
import logging
import os
from logging.config import fileConfig
import connexion
from fuji_server import encoder
from fuji_server.helper.preprocessor import Preprocessor

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

    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH)
    logger.info('Total metrics defined: {}'.format(preproc.get_total_metrics()))

    isDebug = config.getboolean('SERVICE', 'debug_mode')
    preproc.retrieve_licenses(SPDX_URL, isDebug)
    preproc.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    preproc.retrieve_metadata_standards(METADATACATALOG_API, isDebug)
    #preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, bioportal_api=BIOPORTAL_REST, bioportal_key=BIOPORTAL_APIKEY, isDebugMode=False)
    preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)
    preproc.retrieve_common_namespaces()

    logger.info('Total SPDX licenses : {}'.format(preproc.get_total_licenses()))
    logger.info('Total re3repositories found from datacite api : {}'.format(len(preproc.getRE3repositories())))
    logger.info('Total subjects area of imported metadata standards : {}'.format(len(preproc.metadata_standards)))
    logger.info('Total LD vocabs imported : {}'.format(len(preproc.getLinkedVocabs())))
    logger.info('Total common namespaces : {}'.format(len(preproc.getCommonNamespaces())))

    #you can also use Tornado or gevent as the HTTP server, to do so set server to tornado or gevent
    app = connexion.FlaskApp(__name__, specification_dir=YAML_DIR)
    API_YAML = os.path.join(ROOT_DIR, YAML_DIR, config['SERVICE']['swagger_yaml'])
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(API_YAML, arguments={'title': 'F-UJI : FAIRsFAIR Research Data Object Assessment Service'}, validate_responses=False)
    # app.add_api(API_YAML, arguments={'title': 'FAIRsFAIR Research Data Object Assessment Service'}, validate_responses=False, pythonic_params=True)
    #app.run(port=int(config['SERVICE']['service_port']), ssl_context='adhoc')
    app.run(port=int(config['SERVICE']['service_port']))

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # add a new command line option, call it '-c' and set its destination to 'config_file'
    # parser.add_argument("-c", action="store", help='specify the path of the config file (server.ini)', dest="config_file",required=True)
    # get the result
    config = ConfigParser.ConfigParser()
    # config.read(parser.parse_args().config_file)
    my_path = os.path.abspath(os.path.dirname(__file__))
    ini_path = os.path.join(my_path, 'config', 'server_local.ini')
    config.read(ini_path)
    log_config_path = os.path.join(my_path, 'config', 'logging.ini')
    log_directory = os.path.join(my_path, 'logs')
    log_file_path = os.path.join(log_directory, 'fuji.log')
    if not os.path.exists(log_directory):  # FileHandler will create the log file if it does not exist, not directory
        os.makedirs(log_directory, exist_ok=True)
    fileConfig(log_config_path, defaults={'logfilename': log_file_path.replace("\\", "/")})
    logger = logging.getLogger()  # use this form to initialize the root logger
    main()
