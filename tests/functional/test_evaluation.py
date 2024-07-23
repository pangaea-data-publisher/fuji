# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from requests.auth import _basic_auth_str

if TYPE_CHECKING:
    from flask.testing import FlaskClient

DEBUG = True
UID = "https://doi.org/10.5281/zenodo.8347772"
UID_SOFTWARE = "https://github.com/pangaea-data-publisher/fuji"
HTTP_200_OK = 200


# TODO: Re-enable the vcr canning
# @pytest.mark.vcr
def test_evaluation(client: FlaskClient) -> None:
    """Functional test of the /evaluate endpoint.

    This test uses canned http responses from Zenodo and other web services (2023-09-22).
    It compares a stored summary of a live test run on 2023-09-022.
    """
    payload = {"object_identifier": UID, "test_debug": True, "use_datacite": True}
    headers = {
        "Authorization": _basic_auth_str("marvel", "wonderwoman"),
    }
    valid_url = "/fuji/api/v1/evaluate"
    response = client.post(valid_url, json=payload, headers=headers)
    assert response.status_code == HTTP_200_OK

    # these are the results from 2023-09-22
    expected = {
        "maturity": {
            "A": 2,
            "A1": 2,
            "F": 2,
            "F1": 3,
            "F2": 3,
            "F3": 0,
            "F4": 2,
            "FAIR": 2.25,
            "I": 3,
            "I1": 3,
            "I2": 3,
            "I3": 3,
            "R": 2,
            "R1": 1,
            "R1.1": 3,
            "R1.2": 2,
            "R1.3": 2,
        },
        "score_earned": {
            "A": 2,
            "A1": 2,
            "F": 6,
            "F1": 2,
            "F2": 2,
            "F3": 0,
            "F4": 2,
            "FAIR": 17.0,
            "I": 4,
            "I1": 2,
            "I2": 1,
            "I3": 1,
            "R": 5,
            "R1": 1,
            "R1.1": 2,
            "R1.2": 1,
            "R1.3": 1,
        },
        "score_percent": {
            "A": 66.67,
            "A1": 66.67,
            "F": 85.71,
            "F1": 100.0,
            "F2": 100.0,
            "F3": 0.0,
            "F4": 100.0,
            "FAIR": 70.83,
            "I": 100.0,
            "I1": 100.0,
            "I2": 100.0,
            "I3": 100.0,
            "R": 50.0,
            "R1": 25.0,
            "R1.1": 100.0,
            "R1.2": 50.0,
            "R1.3": 50.0,
        },
        "score_total": {
            "A": 3,
            "A1": 3,
            "F": 7,
            "F1": 2,
            "F2": 2,
            "F3": 1,
            "F4": 2,
            "FAIR": 24.0,
            "I": 4,
            "I1": 2,
            "I2": 1,
            "I3": 1,
            "R": 10,
            "R1": 4,
            "R1.1": 2,
            "R1.2": 2,
            "R1.3": 2,
        },
        "status_passed": {
            "A": 2,
            "A1": 2,
            "F": 4,
            "F1": 2,
            "F2": 1,
            "F3": 0,
            "F4": 1,
            "FAIR": 13,
            "I": 3,
            "I1": 1,
            "I2": 1,
            "I3": 1,
            "R": 4,
            "R1": 1,
            "R1.1": 1,
            "R1.2": 1,
            "R1.3": 1,
        },
        "status_total": {
            "A": 3,
            "A1": 3,
            "F": 5,
            "F1": 2,
            "F2": 1,
            "F3": 1,
            "F4": 1,
            "FAIR": 16,
            "I": 3,
            "I1": 1,
            "I2": 1,
            "I3": 1,
            "R": 5,
            "R1": 1,
            "R1.1": 1,
            "R1.2": 1,
            "R1.3": 2,
        },
    }
    response_json = response.json()
    assert response_json["summary"].keys() == expected.keys()


@pytest.mark.vcr()
def test_evaluation_software(client: FlaskClient) -> None:
    """Functional test of the /evaluate endpoint.

    This test uses canned http responses from Github and other web services (2024-01-12).
    It compares a stored summary of a live test run on 2024-01-12.
    """
    payload = {
        "object_identifier": UID_SOFTWARE,
        "test_debug": True,
        "use_datacite": True,
        "use_github": True,
        "metric_version": "metrics_v0.7_software",
    }
    headers = {
        "Authorization": _basic_auth_str("marvel", "wonderwoman"),
    }
    valid_url = "http://localhost:1071/fuji/api/v1/evaluate"
    response = client.post(valid_url, json=payload, headers=headers)
    assert response.status_code == HTTP_200_OK

    # these are the results from 2024-05-03
    expected = {
        "score_earned": {
            "A": 0,
            "F": 0,
            "I": 0,
            "R": 4,
            "A1": 0,
            "F1": 0,
            "F1.1": 0,
            "F1.2": 0,
            "F2": 0,
            "F3": 0,
            "F4": 0,
            "I1": 0,
            "I2": 0,
            "R1": 0,
            "R1.1": 4,
            "R1.2": 0,
            "FAIR": 4.0,
        },
        "score_total": {
            "A": 2,
            "F": 20,
            "I": 7,
            "R": 16,
            "A1": 2,
            "F1": 3,
            "F1.1": 3,
            "F1.2": 3,
            "F2": 6,
            "F3": 2,
            "F4": 3,
            "I1": 6,
            "I2": 1,
            "R1": 8,
            "R1.1": 5,
            "R1.2": 3,
            "FAIR": 45.0,
        },
        "score_percent": {
            "A": 0.0,
            "F": 0.0,
            "I": 0.0,
            "R": 25.0,
            "A1": 0.0,
            "F1": 0.0,
            "F1.1": 0.0,
            "F1.2": 0.0,
            "F2": 0.0,
            "F3": 0.0,
            "F4": 0.0,
            "I1": 0.0,
            "I2": 0.0,
            "R1": 0.0,
            "R1.1": 80.0,
            "R1.2": 0.0,
            "FAIR": 8.89,
        },
        "status_total": {
            "A1": 1,
            "F1": 1,
            "F1.1": 1,
            "F1.2": 1,
            "F2": 2,
            "F3": 1,
            "F4": 1,
            "I1": 2,
            "I2": 1,
            "R1": 3,
            "R1.1": 2,
            "R1.2": 1,
            "A": 1,
            "F": 7,
            "I": 3,
            "R": 6,
            "FAIR": 17,
        },
        "status_passed": {
            "A1": 0,
            "F1": 0,
            "F1.1": 0,
            "F1.2": 0,
            "F2": 0,
            "F3": 0,
            "F4": 0,
            "I1": 0,
            "I2": 0,
            "R1": 0,
            "R1.1": 2,
            "R1.2": 0,
            "A": 0,
            "F": 0,
            "I": 0,
            "R": 2,
            "FAIR": 2,
        },
        "maturity": {
            "A": 0,
            "F": 0,
            "I": 0,
            "R": 1,
            "A1": 0,
            "F1": 0,
            "F1.1": 0,
            "F1.2": 0,
            "F2": 0,
            "F3": 0,
            "F4": 0,
            "I1": 0,
            "I2": 0,
            "R1": 0,
            "R1.1": 3,
            "R1.2": 0,
            "FAIR": 1.0,
        },
    }
    response_json = response.json()
    assert response_json["summary"] == expected
