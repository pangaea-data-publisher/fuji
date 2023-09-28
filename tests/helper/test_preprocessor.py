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
import json
from typing import Any, Dict, List

import pytest
import yaml

from fuji_server.helper.preprocessor import Preprocessor
from tests.conftest import DATA_DIR

isDebug = True


def load_json_from_data_directory(filename: str):
    path = DATA_DIR.joinpath(filename)
    return json.loads(path.read_text())


def load_yaml_from_data_directory(filename: str):
    path = DATA_DIR.joinpath(filename)
    return yaml.safe_load(path.read_text())


def load_txt_from_data_directory(filename: str):
    path = DATA_DIR.joinpath(filename)
    return path.read_text()


@pytest.fixture(scope="session")
def licenses():
    return load_json_from_data_directory("licenses.json")


@pytest.fixture(scope="session")
def metadata_standards():
    return load_json_from_data_directory("metadata_standards.json")


@pytest.fixture(scope="session")
def repodois():
    return load_yaml_from_data_directory("repodois.yaml")


@pytest.fixture(scope="session")
def metadata_standards_uris():
    return load_json_from_data_directory("metadata_standards_uris.json")


@pytest.fixture(scope="session")
def science_formats():
    return load_json_from_data_directory("science_formats.json")


@pytest.fixture(scope="session")
def linked_vocab():
    return load_json_from_data_directory("linked_vocab.json")


@pytest.fixture(scope="session")
def identifiers_org_resolver_data():
    return load_json_from_data_directory("identifiers_org_resolver_data.json")


@pytest.fixture(scope="session")
def jsonldcontext():
    return load_json_from_data_directory("jsonldcontext.json")


@pytest.fixture(scope="session")
def longterm_formats():
    return load_json_from_data_directory("longterm_formats.json")


@pytest.fixture(scope="session")
def open_formats():
    return load_json_from_data_directory("open_formats.json")


@pytest.fixture(scope="session")
def standard_uri_protocols():
    return load_json_from_data_directory("standard_uri_protocols.json")


@pytest.fixture(scope="session")
def default_namespaces():
    txt = load_txt_from_data_directory("default_namespaces.txt").rstrip()
    return [line.rstrip() for line in txt.split("\n")]


@pytest.fixture(scope="session")
def resource_types():
    txt = load_txt_from_data_directory("ResourceTypes.txt").rstrip()
    return [line.rstrip() for line in txt.split("\n")]


@pytest.fixture(scope="session")
def creativeworktypes():
    txt = load_txt_from_data_directory("creativeworktypes.txt").rstrip()
    return [line.rstrip() for line in txt.split("\n")]


@pytest.fixture(scope="session")
def bioschemastypes():
    txt = load_txt_from_data_directory("bioschemastypes.txt").rstrip()
    return [line.rstrip() for line in txt.split("\n")]


@pytest.mark.vcr
def test_set_mime_types(temporary_preprocessor: Preprocessor, initial_mime_types_count) -> None:
    num_types_before = initial_mime_types_count

    temporary_preprocessor.set_mime_types()

    from mimetypes import types_map

    num_types_after = len(types_map)
    assert num_types_after > num_types_before


def test_retrieve_licenses(temporary_preprocessor: Preprocessor, licenses: List[Dict[str, Any]]) -> None:
    assert temporary_preprocessor.total_licenses == 0
    temporary_preprocessor.retrieve_licenses(isDebug)
    expected = len(licenses)
    assert temporary_preprocessor.total_licenses == expected
    assert len(temporary_preprocessor.all_licenses) == temporary_preprocessor.total_licenses
    expected = licenses[0].get("licenseId")
    actual = temporary_preprocessor.all_licenses[0].get("licenseId")
    assert actual == expected


def test_get_licenses(temporary_preprocessor: Preprocessor, licenses: List[Dict[str, Any]]) -> None:
    all_licenses, license_names = temporary_preprocessor.get_licenses()
    expected = len(licenses)
    assert len(all_licenses) == expected
    assert "bsd zero clause license" in license_names


def test_retrieve_datacite_re3repos(temporary_preprocessor: Preprocessor, repodois: Dict[str, str]) -> None:
    assert not temporary_preprocessor.re3repositories
    temporary_preprocessor.retrieve_datacite_re3repos()
    expected = len(repodois)
    assert len(temporary_preprocessor.re3repositories) == expected


def test_retrieve_metadata_standards(temporary_preprocessor: Preprocessor, metadata_standards) -> None:
    assert not temporary_preprocessor.metadata_standards
    temporary_preprocessor.retrieve_metadata_standards()
    expected = len(metadata_standards)
    assert len(temporary_preprocessor.metadata_standards) == expected


def test_retrieve_linkedvocabs(
    temporary_preprocessor: Preprocessor, test_config: Dict, linked_vocab: List[Dict[str, str]]
) -> None:
    LOV_API = test_config["EXTERNAL"]["lov_api"]
    LOD_CLOUDNET = test_config["EXTERNAL"]["lod_cloudnet"]
    assert not temporary_preprocessor.linked_vocabs
    temporary_preprocessor.retrieve_linkedvocabs(lov_api=LOV_API, lodcloud_api=LOD_CLOUDNET, isDebugMode=isDebug)
    expected = len(linked_vocab)
    assert len(temporary_preprocessor.linked_vocabs) == expected


def test_retrieve_default_namespaces(temporary_preprocessor: Preprocessor, default_namespaces) -> None:
    assert not temporary_preprocessor.default_namespaces
    temporary_preprocessor.retrieve_default_namespaces()
    expected = len(default_namespaces)
    assert len(temporary_preprocessor.default_namespaces) == expected
