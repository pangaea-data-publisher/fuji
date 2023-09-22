from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from requests.auth import _basic_auth_str

if TYPE_CHECKING:
    from flask.testing import FlaskClient

DEBUG = True
UID = "https://doi.org/10.5281/zenodo.8347772"
HTTP_200_OK = 200


@pytest.mark.vcr
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
    assert response.json["summary"] == expected
