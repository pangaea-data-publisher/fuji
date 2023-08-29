# -*- coding: utf-8 -*-
"""
Here we test the Preprocessor class which provides the reference data for a server

Comments to this:
Preprocessor is a singleton, therefore we need to proper tear it up and down.

isDebug=True read the files in fuji_server/data
isDebug=False, run harvesting code

All CI tests should be run with isDebug=True, to not call harvester code
Alternative one would have to mock the server responses to not make real calls.

To test if the harvesting still works there are tests taked with the -noCI and -manual
markers. These tests can be run prior to a release manually.
They mock the fuji_server/data path to not override the files under fuji server

"""
isDebug = True
fuji_server_dir = './data_test/'


def test_preprocessor_licences(test_config, temp_preprocessor):
    """Test preprocessor if retrieve_licences works"""

    SPDX_URL = test_config['EXTERNAL']['spdx_license_github']
    assert temp_preprocessor.total_licenses == 0

    temp_preprocessor.retrieve_licenses(SPDX_URL, isDebug)
    assert temp_preprocessor.total_licenses > 0
    assert len(temp_preprocessor.all_licenses) == temp_preprocessor.total_licenses


def test_preprocessor_re3repos(test_config, temp_preprocessor):
    """Test preprocessor if retrieve_re3repos works"""

    DATACITE_API_REPO = test_config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = test_config['EXTERNAL']['re3data_api']

    assert len(temp_preprocessor.re3repositories.keys()) == 0  # this is initialized why?

    temp_preprocessor.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)

    assert temp_preprocessor.re3repositories
    assert len(temp_preprocessor.re3repositories.keys()) > 10
    #print(len(temp_preprocessor.re3repositories.keys()))


def test_preprocessor_metadata_standards(test_config, temp_preprocessor):
    """Test preprocessor if retrieve_metadata_standards works"""

    METADATACATALOG_API = test_config['EXTERNAL']['metadata_catalog']

    assert not temp_preprocessor.metadata_standards

    temp_preprocessor.retrieve_metadata_standards(METADATACATALOG_API, isDebug)

    assert temp_preprocessor.metadata_standards
    print(temp_preprocessor.metadata_standards)
    assert len(temp_preprocessor.metadata_standards.keys()) > 10


def test_preprocessor_retrieve_linkedvocabs(test_config, temp_preprocessor):
    """Test preprocessor if retrieve_linkedvocabs works"""

    LOV_API = test_config['EXTERNAL']['lov_api']
    LOD_CLOUDNET = test_config['EXTERNAL']['lod_cloudnet']
    assert not temp_preprocessor.linked_vocabs

    temp_preprocessor.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)

    assert temp_preprocessor.linked_vocabs
    assert len(temp_preprocessor.linked_vocabs) > 10


def test_preprocessor_rest(test_config, temp_preprocessor):
    """Test preprocessor if others works"""

    METADATACATALOG_API = test_config['EXTERNAL']['metadata_catalog']

    assert not temp_preprocessor.default_namespaces

    temp_preprocessor.retrieve_default_namespaces()
    assert len(temp_preprocessor.default_namespaces) > 10
