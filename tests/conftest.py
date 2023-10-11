from __future__ import annotations

import configparser
import shutil
import time
from mimetypes import types_map
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from fuji_server.app import create_app
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


INITIAL_MIME_TYPES_COUNT = len(types_map)
INITITAL_PREPROCESSOR_STATE = save_preprocessor_state()


@pytest.fixture(scope="session")
def initial_mime_types_count():
    """Initial number of mime types from mimetypes library."""
    return INITIAL_MIME_TYPES_COUNT


@pytest.fixture(scope="session")
def test_config():
    """Fixture returning the read config object by configparser"""
    config = configparser.ConfigParser()
    config.read(TEST_CONFIG_FILE_PATH)
    return config


@pytest.fixture
def temporary_data_directory(tmp_path):
    """Create a temporary data directory and copy fuji_server/data into it."""
    data_directory = tmp_path.joinpath("data")
    shutil.copytree(DATA_DIR, data_directory)
    return tmp_path


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

    # mock getmtime to suppress downloading repo information
    with mock.patch("os.path.getmtime") as mock_getmtime:
        seconds_since_epoch = int(time.time())
        mock_getmtime.return_value = seconds_since_epoch
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
def temporary_preprocessor(temporary_data_directory) -> Preprocessor:
    """Fixture which resets the Preprocessor (singleton) for a test and restores its prior state afterwards"""

    current_state = save_preprocessor_state()
    restore_preprocessor_state(INITITAL_PREPROCESSOR_STATE)

    # point the preprocessor to a temporary directory,
    # to not change the fuji_server/data contents when running tests
    Preprocessor.fuji_server_dir = temporary_data_directory
    yield Preprocessor
    restore_preprocessor_state(current_state)


@pytest.fixture(scope="session")
def app(test_config) -> Flask:
    _app = create_app(test_config)
    _app.testing = True
    return _app.app


@pytest.fixture(scope="session")
def client(app: Flask) -> FlaskClient:
    with app.test_client() as test_client:
        yield test_client
