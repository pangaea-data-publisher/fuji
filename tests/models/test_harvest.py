# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import pytest

from fuji_server.models.harvest import Harvest

DOI = "https://doi.org/10.1594/PANGAEA.902845"
AUTH_TOKEN = "password"


@pytest.fixture
def harvest():
    return Harvest(object_identifier=DOI)


def test_to_dict(harvest):
    result = harvest.to_dict()
    assert result["object_identifier"] == DOI


def test_from_dict():
    values = {"object_identifier": DOI}
    instance = Harvest.from_dict(values)
    assert instance._object_identifier == DOI


def test_set_object_identifier(harvest):
    valid_doi = "other-doi"
    harvest.object_identifier = valid_doi
    assert harvest._object_identifier == valid_doi
    invalid_doi = None
    with pytest.raises(ValueError):
        harvest.object_identifier = invalid_doi


def test_set_auth_token(harvest):
    harvest.auth_token = AUTH_TOKEN
    assert harvest._auth_token == AUTH_TOKEN


def test_set_auth_token_type(harvest):
    valid_auth_token_type = "Bearer"
    harvest.auth_token_type = valid_auth_token_type
    assert harvest._auth_token_type == valid_auth_token_type
    invalid_auth_token_type = "Bear"
    with pytest.raises(ValueError):
        harvest.auth_token_type = invalid_auth_token_type
