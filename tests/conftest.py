"""
Configurations and fixtures for fuji_server tests
"""
import configparser
from mimetypes import types_map
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from fuji_server.app.fuji_app import create_fuji_app
from fuji_server.helper.preprocessor import Preprocessor

if TYPE_CHECKING:
    from flask.app import Flask
    from flask.testing import FlaskClient

ROOT_DIR = Path(__file__).parent.parent
SRC_DIR = ROOT_DIR.joinpath("fuji_server")
DATA_DIR = SRC_DIR.joinpath("data")
TESTS_DIR = ROOT_DIR.joinpath("tests")
TEST_CONFIG_FILE_PATH = TESTS_DIR.joinpath("config", "test_server.ini")


def save_preprocessor_state():
    return {k: v for k, v in vars(Preprocessor).items() if not (k.startswith(("_", "get", "set", "retrieve")))}


def restore_preprocessor_state(state):
    for k, v in state.items():
        setattr(Preprocessor, k, v)


INITITAL_PREPROCESSOR_STATE = save_preprocessor_state()
NUM_KNOWN_TYPES = len(types_map)


@pytest.fixture(scope="session")
def num_known_types() -> int:
    return NUM_KNOWN_TYPES


@pytest.fixture(scope="session")
def vcr_cassette_dir(request):
    return str(TESTS_DIR.joinpath("data", "cassettes"))


@pytest.fixture(scope="session")
def test_config():
    """Fixture returning the read config object by configparser"""
    config = configparser.ConfigParser()
    config.read(TEST_CONFIG_FILE_PATH)
    return config


@pytest.fixture(scope="session", autouse=True)
def preprocessor(test_config) -> Preprocessor:
    YAML_DIR = test_config["SERVICE"]["yaml_directory"]
    METRIC_YML_PATH = SRC_DIR.joinpath(YAML_DIR)
    LOV_API = test_config["EXTERNAL"]["lov_api"]
    LOD_CLOUDNET = test_config["EXTERNAL"]["lod_cloudnet"]

    preprocessor = Preprocessor()
    preprocessor.set_metric_yaml_path(METRIC_YML_PATH)
    isDebug = True
    preprocessor.retrieve_licenses(isDebug)
    preprocessor.retrieve_datacite_re3repos()
    preprocessor.retrieve_metadata_standards()
    preprocessor.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)
    preprocessor.retrieve_default_namespaces()
    preprocessor.set_remote_log_info(
        test_config["SERVICE"]["remote_log_host"],
        test_config["SERVICE"]["remote_log_path"],
    )
    return preprocessor


@pytest.fixture
def temporary_preprocessor() -> Preprocessor:
    """Fixture which resets the Preprocessor (singleton) for a test and restores its prior state afterwards"""

    current_state = save_preprocessor_state()
    restore_preprocessor_state(INITITAL_PREPROCESSOR_STATE)
    yield Preprocessor
    restore_preprocessor_state(current_state)


@pytest.fixture(scope="session")
def app(test_config) -> "Flask":
    _app = create_fuji_app(test_config)
    _app.testing = True
    return _app.app


@pytest.fixture(scope="session")
def client(app: "Flask") -> "FlaskClient":
    with app.test_client() as test_client:
        yield test_client
