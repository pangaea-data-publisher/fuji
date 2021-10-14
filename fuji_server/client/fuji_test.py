#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser as ConfigParser
import json
import os
from pathlib import Path
from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.helper.preprocessor import Preprocessor

identifier = 'https://doi.org/10.1594/PANGAEA.902845'
oai_pmh = 'http://ws.pangaea.de/oai/'
debug = True


def main():
    config = ConfigParser.ConfigParser()
    my_path = Path(__file__).parent.parent
    ini_path = os.path.join(my_path, 'config', 'server.ini')
    config.read(ini_path)
    YAML_DIR = config['SERVICE']['yaml_directory']
    METRIC_YAML = config['SERVICE']['metrics_yaml']
    METRIC_YML_PATH = os.path.join(my_path, YAML_DIR, METRIC_YAML)
    SPDX_URL = config['EXTERNAL']['spdx_license_github']
    DATACITE_API_REPO = config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = config['EXTERNAL']['re3data_api']
    METADATACATALOG_API = config['EXTERNAL']['metadata_catalog']
    isDebug = config.getboolean('SERVICE', 'debug_mode')

    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH)
    print(f'Total metrics defined: {preproc.get_total_metrics()}')

    isDebug = config.getboolean('SERVICE', 'debug_mode')
    preproc.retrieve_licenses(SPDX_URL, isDebug)
    preproc.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    preproc.retrieve_metadata_standards(METADATACATALOG_API, isDebug)

    print(f'Total SPDX licenses : {preproc.get_total_licenses()}')
    print(f'Total re3repositories found from datacite api : {len(preproc.getRE3repositories())}')
    print(f'Total subjects area of imported metadata standards : {len(preproc.metadata_standards)}')

    ft = FAIRCheck(uid=identifier, oai=oai_pmh, test_debug=debug)
    uid_result, pid_result = ft.check_unique_persistent()
    core_metadata_result = ft.check_minimal_metatadata()
    content_identifier_included_result = ft.check_content_identifier_included()
    check_searchable_result = ft.check_searchable()
    license_result = ft.check_license()
    relatedresources_result = ft.check_relatedresources()
    results = [uid_result, pid_result, core_metadata_result, content_identifier_included_result, license_result]
    # put the debug messages at the right place...
    for result_index, result in enumerate(results):
        results[result_index]['test_debug'] = ft.msg_filter.getMessage(result.get('metric_identifier'))

    print(json.dumps(results, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
