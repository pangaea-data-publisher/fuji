# -*- coding: utf-8 -*-
import configparser as ConfigParser
import json
import os
import pytest
from pathlib import Path
from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.helper.preprocessor import Preprocessor

THIS_PATH = Path(__file__).parent
identifiers = ['https://doi.org/10.1594/PANGAEA.902845']
oai_pmhs = ['http://ws.pangaea.de/oai/']
# the #f-uji.net eval is slightly different here...
reference_files = [os.path.join(THIS_PATH, './json_ref_data/10.1594_PANGAEA.902845_sum.json')]
summaries_should = []
for ref in reference_files:
    with open(ref, 'r', encoding='utf-8') as file_o:
        data = json.load(file_o)
        summaries_should.append(data)#['summary']['score_percent'])
  
debug = True

# Maybe change such that on changes test data can easily be updated
@pytest.mark.parametrize('identifier, oai_pmh, summary_expected', zip(identifiers, oai_pmhs, summaries_should))
def test_fair_check(identifier, oai_pmh, summary_expected):
    """Full regression test of the FAIR check for a certain

    pids and oai_pmh endpoints. Currently we only test if the summary is the same
    not if all the log details and so on also are.
    These tests may take long.
    """
 
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
        uid_result, pid_result, core_metadata_result, content_identifier_included_result, check_searchable_result,
        access_level_result, formal_representation_result, semantic_vocabulary_result, license_result,
        data_file_format_result, data_provenance_result, relatedresources_result, community_standards_result,
        data_content_metadata, metadata_preserved_result, standard_protocol_data_result,
        standard_protocol_metadata_result
    ]

    logmessages = ft.get_log_messages_dict()
    summary = ft.get_assessment_summary(results)
    print(summary)

    assert summary_expected == summary#['score_percent']
