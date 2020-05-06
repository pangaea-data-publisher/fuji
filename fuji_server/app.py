#!/usr/bin/env python3

import argparse
import configparser as ConfigParser
import os
from logging.config import fileConfig

# # Create a URL route in our application for "/"
# @app.route("/")
# def home():
#     """
#     This function just responds to the browser URL
#     localhost:1071/
#     :return:        the rendered template "home.html"
#     """
#     return render_template("home.html")
from fuji_server import encoder
from fuji_server.controllers import *
from fuji_server.controllers.preprocessor import Preprocessor


def main():
    logging.getLogger('connexion.operation').setLevel('INFO')
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    YAML_DIR = config['SERVICE']['yaml_directory']
    METRIC_YAML = config['SERVICE']['metrics_yaml']
    METRIC_YML_PATH = os.path.join(ROOT_DIR, YAML_DIR+'/'+METRIC_YAML)
    SPDX_URL = config['EXTERNAL']['spdx_license_github']
    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH)
    preproc.retrieve_licenses(SPDX_URL)
    logger.info('Total metrics defined: {}'.format(preproc.get_total_metrics()))
    logger.info('Total SPDX licenses : {}'.format(preproc.get_total_licenses()))

    app = connexion.FlaskApp(__name__, specification_dir=YAML_DIR)
    API_YAML = os.path.join(ROOT_DIR, YAML_DIR+'/'+config['SERVICE']['swagger_yaml'])
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api(API_YAML, arguments={'title': 'FUJI - FAIR Data Assessment Service'}, validate_responses=False)
    #app.add_api(API_YAML, arguments={'title': 'FAIRsFAIR Data Assessment Service'},validate_responses=False,pythonic_params=True)
    app.run(port=int(config['SERVICE']['service_port']))

if __name__ == '__main__':
    #parser = argparse.ArgumentParser()
    # add a new command line option, call it '-c' and set its destination to 'config_file'
    #parser.add_argument("-c", action="store", help='specify the path of the config file (server.ini)', dest="config_file",required=True)
    # get the result
    config = ConfigParser.ConfigParser()
    #config.read(parser.parse_args().config_file)
    my_path = os.path.abspath(os.path.dirname(__file__))
    ini_path = os.path.join(my_path,'config','server.ini')
    config.read(ini_path)
    log_config_path = os.path.join(my_path,'config','logging.ini')
    log_file_path = os.path.join(my_path, 'logs', 'fuji.log')
    fileConfig(log_config_path, defaults={'logfilename': log_file_path.replace("\\", "/")} )
    logger = logging.getLogger() # use this form to initialize the root logger
    main()
