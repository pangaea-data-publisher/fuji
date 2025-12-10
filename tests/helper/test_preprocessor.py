# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

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

from typing import Any

import pytest

import yaml
from fuji_server.helper.preprocessor import Preprocessor
from tests.conftest import DATA_DIR

isDebug = True


def load_yaml_from_data_directory(filename: str):
    path = DATA_DIR.joinpath(filename)
    return yaml.safe_load(path.read_text())


def load_txt_from_data_directory(filename: str):
    path = DATA_DIR.joinpath(filename)
    return path.read_text()


@pytest.fixture(scope="session")
def access_rights():
    return load_yaml_from_data_directory("access_rights.yaml")


@pytest.fixture(scope="session")
def licenses():
    return load_yaml_from_data_directory("licenses.yaml")


@pytest.fixture(scope="session")
def metadata_standards():
    return load_yaml_from_data_directory("metadata_standards.yaml")


@pytest.fixture(scope="session")
def repodois():
    return load_yaml_from_data_directory("repodois.yaml")


@pytest.fixture(scope="session")
def linked_vocab():
    return load_yaml_from_data_directory("linked_vocab.yaml")


@pytest.fixture(scope="session")
def identifiers_org_resolver_data():
    return load_yaml_from_data_directory("identifiers_org_resolver_data.yaml")


@pytest.fixture(scope="session")
def jsonldcontext():
    return load_yaml_from_data_directory("jsonldcontext.yaml")


@pytest.fixture(scope="session")
def standard_uri_protocols():
    return load_yaml_from_data_directory("standard_uri_protocols.yaml")


@pytest.fixture(scope="session")
def default_namespaces():
    txt = load_txt_from_data_directory("default_namespaces.txt").rstrip()
    return [line.rstrip() for line in txt.split("\n")]


@pytest.fixture(scope="session")
def resource_types():
    txt = load_txt_from_data_directory("ResourceTypes.txt").rstrip()
    return [line.lower().rstrip() for line in txt.split("\n")]


@pytest.fixture(scope="session")
def creativeworktypes():
    txt = load_txt_from_data_directory("creativeworktypes.txt").rstrip()
    return [line.rstrip() for line in txt.split("\n")]


@pytest.fixture(scope="session")
def bioschemastypes():
    txt = load_txt_from_data_directory("bioschemastypes.txt").rstrip()
    return [line.rstrip() for line in txt.split("\n")]


"""@pytest.mark.vcr
def test_set_mime_types(temporary_preprocessor: Preprocessor, initial_mime_types_count) -> None:
    num_types_before = initial_mime_types_count

    temporary_preprocessor.set_mime_types()

    from mimetypes import types_map

    num_types_after = len(types_map)
    assert num_types_after > num_types_before"""


def test_retrieve_licenses(temporary_preprocessor: Preprocessor, licenses: list[dict[str, Any]]) -> None:
    assert temporary_preprocessor.total_licenses == 0
    temporary_preprocessor.retrieve_licenses(isDebug)
    expected = len(licenses)
    assert temporary_preprocessor.total_licenses == expected
    assert len(temporary_preprocessor.all_licenses) == temporary_preprocessor.total_licenses
    expected = licenses[0].get("licenseId")
    actual = temporary_preprocessor.all_licenses[0].get("licenseId")
    assert actual == expected


def test_get_licenses(temporary_preprocessor: Preprocessor, licenses: list[dict[str, Any]]) -> None:
    all_licenses, license_names = temporary_preprocessor.get_licenses()
    expected = len(licenses)
    assert len(all_licenses) == expected
    assert "bsd zero clause license" in license_names


def test_retrieve_datacite_re3repos(temporary_preprocessor: Preprocessor, repodois: dict[str, str]) -> None:
    assert not temporary_preprocessor.re3repositories
    temporary_preprocessor.retrieve_datacite_re3repos()
    expected = len(repodois)
    assert len(temporary_preprocessor.re3repositories) == expected


def test_retrieve_default_namespaces(temporary_preprocessor: Preprocessor, default_namespaces) -> None:
    assert not temporary_preprocessor.default_namespaces
    temporary_preprocessor.retrieve_default_namespaces()
    expected = len(default_namespaces)
    assert len(temporary_preprocessor.default_namespaces) == expected


def test_get_access_rights(temporary_preprocessor: Preprocessor, access_rights):
    assert not temporary_preprocessor.access_rights
    result = temporary_preprocessor.get_access_rights()
    assert result == access_rights


def test_get_resource_types(temporary_preprocessor: Preprocessor, resource_types):
    assert not temporary_preprocessor.resource_types
    result = temporary_preprocessor.get_resource_types()
    assert result == resource_types
    assert temporary_preprocessor.resource_types == resource_types


def test_get_identifiers_org_data(temporary_preprocessor: Preprocessor, identifiers_org_resolver_data):
    assert not temporary_preprocessor.identifiers_org_data
    result = temporary_preprocessor.get_identifiers_org_data()
    # check a given key in the result dictionary
    expected = {"pattern": "^[a-z][a-z]/[0-9]+$", "url_pattern": "https://w3id.org/oc/corpus/{$id}"}
    assert result["occ"] == expected
    assert temporary_preprocessor.identifiers_org_data["occ"] == expected


def test_get_metadata_standards(temporary_preprocessor: Preprocessor, metadata_standards):
    assert not temporary_preprocessor.metadata_standards
    result = temporary_preprocessor.get_metadata_standards()
    assert result == metadata_standards
    assert temporary_preprocessor.metadata_standards == metadata_standards


def test_get_schema_org_context(temporary_preprocessor: Preprocessor):
    assert not temporary_preprocessor.schema_org_context
    result = temporary_preprocessor.get_schema_org_context()
    assert isinstance(result, list)
    assert "orderpickupavailable" in result
    assert result == temporary_preprocessor.schema_org_context


def test_get_schema_org_creativeworks(temporary_preprocessor: Preprocessor):
    assert not temporary_preprocessor.schema_org_creativeworks
    result = temporary_preprocessor.get_schema_org_creativeworks()
    assert isinstance(result, list)
    assert "3dmodel" in result
    assert result == temporary_preprocessor.schema_org_creativeworks


def test_get_science_file_formats(temporary_preprocessor: Preprocessor):
    assert not temporary_preprocessor.science_file_formats
    result = temporary_preprocessor.get_science_file_formats()
    assert "application/CCP4-mtz" in result
    assert result == temporary_preprocessor.science_file_formats


def test_get_long_term_file_formats(temporary_preprocessor: Preprocessor):
    assert not temporary_preprocessor.long_term_file_formats
    result = temporary_preprocessor.get_long_term_file_formats()
    assert "audio/mp4" in result
    assert result == temporary_preprocessor.long_term_file_formats


def test_get_open_file_formats(temporary_preprocessor: Preprocessor):
    assert not temporary_preprocessor.open_file_formats
    result = temporary_preprocessor.get_open_file_formats()
    assert "audio/mp4" in result
    assert result == temporary_preprocessor.open_file_formats


def test_get_standard_protocols(temporary_preprocessor: Preprocessor, standard_uri_protocols):
    assert not temporary_preprocessor.standard_protocols
    result = temporary_preprocessor.get_standard_protocols()
    assert result == standard_uri_protocols
    assert temporary_preprocessor.standard_protocols == standard_uri_protocols
