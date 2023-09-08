from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask.testing import FlaskClient

HTTP_200_OK = 200


def test_ui_returns_200(client: FlaskClient) -> None:
    valid_url = "/fuji/api/v1/ui/"
    response = client.get(valid_url)
    assert response.status_code == HTTP_200_OK


def test_schema_returns_200(client: FlaskClient) -> None:
    valid_url = "/fuji/api/v1/openapi.json"
    response = client.get(valid_url)
    assert response.status_code == HTTP_200_OK
