import configparser as ConfigParser
import json
import os
import pytest
from pathlib import Path
from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.helper.preprocessor import Preprocessor


# rather use pytest regressions for results check?
# refactor to Read these from files at some point
identifiers = ['https://doi.org/10.1594/PANGAEA.902845']
oai_pmhs = ['http://ws.pangaea.de/oai/']
summaries_should = [{'score_earned': {'A': 4, 'F': 7, 'I': 3, 'R': 7, 'A1': 3, 'A2': 1, 'F1': 2, 'F2': 2, 'F3': 1, 'F4': 2, 'I1': 2, 'I3': 1, 'R1': 2, 'R1.1': 2, 'R1.2': 1, 'R1.3': 2, 'FAIR': 21.0}, 'score_total': {'A': 4, 'F': 7, 'I': 4, 'R': 10, 'A1': 3, 'A2': 1, 'F1': 2, 'F2': 2, 'F3': 1, 'F4': 2, 'I1': 3, 'I3': 1, 'R1': 4, 'R1.1': 2, 'R1.2': 2, 'R1.3': 2, 'FAIR': 25.0}, 'score_percent': {'A': 100.0, 'F': 100.0, 'I': 75.0, 'R': 70.0, 'A1': 100.0, 'A2': 100.0, 'F1': 100.0, 'F2': 100.0, 'F3': 100.0, 'F4': 100.0, 'I1': 66.67, 'I3': 100.0, 'R1': 50.0, 'R1.1': 100.0, 'R1.2': 50.0, 'R1.3': 100.0, 'FAIR': 84.0}, 'status_total': {'A1': 3, 'A2': 1, 'F1': 2, 'F2': 1, 'F3': 1, 'F4': 1, 'I1': 2, 'I3': 1, 'R1': 1, 'R1.1': 1, 'R1.2': 1, 'R1.3': 2, 'A': 4, 'F': 5, 'I': 3, 'R': 5, 'FAIR': 17}, 'status_passed': {'A1': 3, 'A2': 1, 'F1': 2, 'F2': 1, 'F3': 1, 'F4': 1, 'I1': 1, 'I3': 1, 'R1': 1, 'R1.1': 1, 'R1.2': 1, 'R1.3': 2, 'A': 4, 'F': 5, 'I': 2, 'R': 5, 'FAIR': 16}, 'maturity': {'A': 3, 'F': 3, 'I': 2, 'R': 2, 'A1': 3, 'A2': 3, 'F1': 3, 'F2': 3, 'F3': 3, 'F4': 3, 'I1': 2, 'I3': 3, 'R1': 2, 'R1.1': 3, 'R1.2': 2, 'R1.3': 2, 'FAIR': 2.5}}]

debug = True

@pytest.mark.parametrize("identifier, oai_pmh, summary_expected", zip(identifiers, oai_pmhs, summaries_should))
def test_fair_check(identifier, oai_pmh, summary_expected):
    """Full regression test of the FAIR check for a certain

    pids and oai_pmh endpoints. Currently we only test if the summary is the same
    not if all the log details and so on also are.
    These tests may take long.
    """
    config = ConfigParser.ConfigParser()
    my_path = Path(__file__).parent.parent.parent
    print(my_path)
    ini_path = os.path.join(my_path, 'fuji_server', 'config', 'server.ini')
    print(ini_path)
    config.read(ini_path)
    YAML_DIR = config['SERVICE']['yaml_directory']
    METRIC_YAML = config['SERVICE']['metrics_yaml']
    METRIC_YML_PATH = os.path.join(my_path, 'fuji_server',  YAML_DIR, METRIC_YAML)
    SPDX_URL = config['EXTERNAL']['spdx_license_github']
    DATACITE_API_REPO = config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = config['EXTERNAL']['re3data_api']
    METADATACATALOG_API = config['EXTERNAL']['metadata_catalog']
    isDebug = config.getboolean('SERVICE', 'debug_mode')

    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH, limit=3, specification_uri=None)
    print(f'Total metrics defined: {preproc.get_total_metrics()}')

    isDebug = config.getboolean('SERVICE', 'debug_mode')
    preproc.retrieve_licenses(SPDX_URL, isDebug)
    preproc.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    preproc.retrieve_metadata_standards(METADATACATALOG_API, isDebug)

    print(f'Total SPDX licenses : {preproc.get_total_licenses()}')
    print(f'Total re3repositories found from datacite api : {len(preproc.getRE3repositories())}')
    print(f'Total subjects area of imported metadata standards : {len(preproc.metadata_standards)}')

    ft = FAIRCheck(uid=identifier, oaipmh_endpoint=oai_pmh, test_debug=debug)
    uid_result, pid_result = ft.check_unique_persistent()
    ft.retrieve_metadata_embedded(ft.extruct_result)
    include_embedded = True
    if ft.repeat_pid_check:
        uid_result, pid_result = ft.check_unique_persistent()
    ft.retrieve_metadata_external()
    if ft.repeat_pid_check:
        uid_result, pid_result = ft.check_unique_persistent()
    core_metadata_result = ft.check_minimal_metatadata()
    content_identifier_included_result = ft.check_content_identifier_included()
    access_level_result = ft.check_data_access_level()
    license_result = ft.check_license()
    relatedresources_result = ft.check_relatedresources()
    check_searchable_result = ft.check_searchable()
    data_content_metadata = ft.check_data_content_metadata()
    data_file_format_result = ft.check_data_file_format()
    community_standards_result = ft.check_community_metadatastandards()
    data_provenance_result = ft.check_data_provenance()
    formal_representation_result = ft.check_formal_metadata()
    semantic_vocabulary_result = ft.check_semantic_vocabulary()
    metadata_preserved_result = ft.check_metadata_preservation()
    standard_protocol_metadata_result = ft.check_standardised_protocol_metadata()
    standard_protocol_data_result = ft.check_standardised_protocol_data()
    results = [
        uid_result, pid_result, core_metadata_result, content_identifier_included_result,
        check_searchable_result, access_level_result, formal_representation_result, semantic_vocabulary_result,
        license_result, data_file_format_result, data_provenance_result, relatedresources_result,
        community_standards_result, data_content_metadata, metadata_preserved_result,
        standard_protocol_data_result, standard_protocol_metadata_result
    ]

    logmessages = ft.get_log_messages_dict()
    summary = ft.get_assessment_summary(results)
    print(summary)

    assert summary_expected == summary