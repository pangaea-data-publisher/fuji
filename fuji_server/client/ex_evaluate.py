#!/usr/bin/env python3

import configparser as ConfigParser
import json
import os
from pathlib import Path
from fuji_server.controllers.fair_test import FAIRTest
from fuji_server.controllers.preprocessor import Preprocessor

identifier = 'https://doi.org/10.1594/PANGAEA.902845'
oai_pmh = 'http://ws.pangaea.de/oai/'
debug = True

def main():
    config = ConfigParser.ConfigParser()
    my_path = Path(__file__).parent.parent
    ini_path = os.path.join(my_path,'config','server.ini')
    config.read(ini_path)
    YAML_DIR = config['SERVICE']['yaml_directory']
    METRIC_YAML = config['SERVICE']['metrics_yaml']
    METRIC_YML_PATH = os.path.join(my_path, YAML_DIR , METRIC_YAML)
    SPDX_URL = config['EXTERNAL']['spdx_license_github']
    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH)
    preproc.retrieve_licenses(SPDX_URL)
    print('Total metrics defined: {}'.format(preproc.get_total_metrics()))
    print('Total SPDX licenses : {}'.format(preproc.get_total_licenses()))

    ft = FAIRTest(uid=identifier, oai=oai_pmh, test_debug=debug)
    uid_result, pid_result = ft.check_unique_persistent()
    core_metadata_result = ft.check_core_metadata()
    identifier_included_result = ft.check_data_identifier_included()
    license_result = ft.check_license()
    results = [uid_result, pid_result, core_metadata_result, identifier_included_result, license_result]
    print(json.dumps(results, indent=4, sort_keys=True))

if __name__ == '__main__':
    main()
