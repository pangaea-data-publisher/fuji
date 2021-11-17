# -*- coding: utf-8 -*-
"""
Configurations and fixtures for fuji_server tests
"""
import os
import pytest
import configparser
import pickle
from pprint import pprint
#from fuji_server import main
from pathlib import Path
from fuji_server.app.fuji_app import create_fuji_app
from fuji_server.helper.preprocessor import Preprocessor

pytest_plugins = ()

THIS_PATH = Path(__file__).parent
TEST_CONFIG_FILE_PATH = os.path.join(THIS_PATH, 'test_server.ini')
config_fuji = configparser.ConfigParser()
config_fuji.read(TEST_CONFIG_FILE_PATH)
flask_app = create_fuji_app(config_fuji)
flask_app.testing = True

##### Add some markers to pytest to group tests
# control skipping test on command line options, for test collection
# https://docs.pytest.org/en/stable/example/simple.html?highlight=pytest_configure


def pytest_configure(config):
    """
    Here you can add things by a pytest config, could be also part of a separate file
    So far we add some markers here to be able to execute a certain group of tests
    We make them all lowercaps as convention
    """
    config.addinivalue_line('markers', 'manual: tests which should be trickered manual only')
    config.addinivalue_line('markers', 'noci: tests which should not run on the CI')
    config.addinivalue_line('markers', 'regression: tests which run a fuji as a whole')
    config.addinivalue_line('markers', 'smoke: tests which run very fast')


@pytest.fixture(scope='session')
def fujiclient():
    """Fixture providing a fuji flask test_client, for real requests to"""
    initialize_preprocessor(config_fuji)
    with flask_app.app.test_client() as test_client:
        #login(test_client, "username", "password")
        yield test_client


def initialize_preprocessor(test_config):
    """Function which populates the preprocessor from __main__"""

    ROOT_DIR = os.path.join(Path(__file__).parent.parent, 'fuji_server')
    YAML_DIR = test_config['SERVICE']['yaml_directory']
    METRIC_YAML = test_config['SERVICE']['metrics_yaml']
    METRIC_YML_PATH = os.path.join(ROOT_DIR, YAML_DIR, METRIC_YAML)
    SPDX_URL = test_config['EXTERNAL']['spdx_license_github']
    DATACITE_API_REPO = test_config['EXTERNAL']['datacite_api_repo']
    RE3DATA_API = test_config['EXTERNAL']['re3data_api']
    METADATACATALOG_API = test_config['EXTERNAL']['metadata_catalog']
    LOV_API = test_config['EXTERNAL']['lov_api']
    LOD_CLOUDNET = test_config['EXTERNAL']['lod_cloudnet']
    data_files_limit = int(test_config['SERVICE']['data_files_limit'])
    metric_specification = test_config['SERVICE']['metric_specification']

    preproc = Preprocessor()
    preproc.retrieve_metrics_yaml(METRIC_YML_PATH, data_files_limit, metric_specification)
    isDebug = True
    preproc.retrieve_licenses(SPDX_URL, isDebug)
    preproc.retrieve_datacite_re3repos(RE3DATA_API, DATACITE_API_REPO, isDebug)
    preproc.retrieve_metadata_standards(METADATACATALOG_API, isDebug)
    preproc.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)
    preproc.retrieve_default_namespaces()
    preproc.set_remote_log_info(test_config['SERVICE']['remote_log_host'], test_config['SERVICE']['remote_log_path'])


@pytest.fixture(scope='function')
def test_config():
    """Fixture returning the read config object by configparser"""

    return config_fuji


@pytest.fixture(scope='function')
def temp_preprocessor():
    """Fixture which resets the Preprocessor (singledton) for a test and restores its prior state afterwards"""
    preproc = Preprocessor

    # save current state
    with open('temp_proprocessor_dump.pkl', 'bw') as fileo:
        pickle.dump(preproc, fileo)

    # reseting the preprocessor (everything from class header)
    preproc.all_metrics_list = []
    preproc.formatted_specification = {}
    preproc.total_metrics = 0
    preproc.total_licenses = 0
    preproc.METRIC_YML_PATH = None
    preproc.SPDX_URL = None
    preproc.DATACITE_API_REPO = None
    preproc.RE3DATA_API = None
    preproc.LOV_API = None
    preproc.LOD_CLOUDNET = None
    preproc.BIOPORTAL_API = None
    preproc.BIOPORTAL_KEY = None
    preproc.schema_org_context = []
    preproc.all_licenses = []
    preproc.license_names = []
    preproc.metadata_standards = {}  # key=subject,value =[standards name]
    preproc.metadata_standards_uris = {}  #some additional namespace uris and all uris from above as key
    preproc.science_file_formats = {}
    preproc.long_term_file_formats = {}
    preproc.open_file_formats = {}
    preproc.re3repositories: Dict[Any, Any] = {}
    preproc.linked_vocabs = {}
    preproc.default_namespaces = []
    preproc.standard_protocols = {}
    preproc.resource_types = []
    preproc.identifiers_org_data = {}
    preproc.google_data_dois = []
    preproc.google_data_urls = []
    #preproc.fuji_server_dir = os.path.dirname(os.path.dirname(__file__))  # project_root
    preproc.header = {'Accept': 'application/json'}
    #preproc.logger = logging.getLogger(__name__)
    preproc.data_files_limit = 3
    preproc.metric_specification = None
    preproc.remote_log_host = None
    preproc.remote_log_path = None

    yield preproc  # test is running

    # tear down code, restore the state
    with open('temp_proprocessor_dump.pkl', 'br') as fileo:
        preproc = pickle.load(fileo)
    os.remove('temp_proprocessor_dump.pkl')
