# -*- coding: utf-8 -*-
"""
Here we test the Preprocessor class which provides the reference data for a server

Comments to this:
Preprocessor is a singledton, therefore we need to proper tear it up and down.

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
    preproc = temp_preprocessor
    assert preproc.total_licenses == 0

    preproc.retrieve_licenses(SPDX_URL, isDebug)
    
    assert preproc.total_licenses > 0
    assert len(preproc.all_licenses) == preproc.total_licenses


def test_preprocessor_re3repos(test_config, temp_preprocessor):
    """Test preprocessor if retrieve_re3repos works"""

    DATACITE_API_REPO = test_config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = test_config['EXTERNAL']['re3data_api']

    assert temp_preprocessor.re3repositories == {} # this is initialized why?

    temp_preprocessor.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    
    assert temp_preprocessor.re3repositories != {}
    assert len(temp_preprocessor.re3repositories.keys()) > 10
    print(len(temp_preprocessor.re3repositories.keys()))
    assert False


def test_preprocessor_metadata_standards(test_config, temp_preprocessor):
    """Test preprocessor if retrieve_metadata_standards works"""

    METADATACATALOG_API = test_config['EXTERNAL']['metadata_catalog']

    assert temp_preprocessor.metadata_standards == {}

    temp_preprocessor.retrieve_metadata_standards(METADATACATALOG_API, isDebug)
    
    assert temp_preprocessor.metadata_standards != {}
    assert len(temp_preprocessor.metadata_standards.keys()) > 10


def test_preprocessor_retrieve_linkedvocabs(test_config, temp_preprocessor):
    """Test preprocessor if retrieve_linkedvocabs works"""
    pass



def test_preprocessor_rest(test_config, temp_preprocessor):
    """Test preprocessor if others works"""

    METADATACATALOG_API = test_config['EXTERNAL']['metadata_catalog']

    temp_preprocessor.retrieve_default_namespaces()
    temp_preprocessor.set_remote_log_info(test_config['SERVICE']['remote_log_host'], test_config['SERVICE']['remote_log_path'])

    pass

"""
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
    data_files_limit = int(config['SERVICE']['data_files_limit'])
    metric_specification = config['SERVICE']['metric_specification']

    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH, data_files_limit, metric_specification)
    isDebug = True
    preproc.retrieve_licenses(SPDX_URL, isDebug)
    preproc.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    preproc.retrieve_metadata_standards(METADATACATALOG_API, isDebug)
    #preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, bioportal_api=BIOPORTAL_REST, bioportal_key=BIOPORTAL_APIKEY, isDebugMode=False)
    preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)
    preproc.retrieve_default_namespaces()
    preproc.set_remote_log_info(config['SERVICE']['remote_log_host'], config['SERVICE']['remote_log_path'])
"""