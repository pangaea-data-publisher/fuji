import pytest

from fuji_server.controllers.fair_check import FAIRCheck

DEBUG = True
UID = "https://doi.org/10.1594/PANGAEA.902845"
OAIPMH_ENDPOINT = "https://ws.pangaea.de/oai/"


@pytest.fixture(scope="session")
def fair_check() -> FAIRCheck:
    return FAIRCheck(uid=UID, oaipmh_endpoint=OAIPMH_ENDPOINT, test_debug=DEBUG)


@pytest.mark.vcr
def test_check_unique_metadata_identifier(fair_check: FAIRCheck) -> None:
    result = fair_check.check_unique_metadata_identifier()
    expected = {"guid": UID, "guid_scheme": "doi"}
    assert result["output"] == expected


@pytest.mark.vcr
def test_harvest_all_metadata(fair_check: FAIRCheck) -> None:
    fair_check.harvest_all_metadata()
    assert fair_check.landing_url == "https://doi.pangaea.de/10.1594/PANGAEA.902845"
    assert fair_check.origin_url == UID
    assert fair_check.pid_url == UID
    assert fair_check.pid_scheme == "doi"
