import pytest
from fuji_server.controllers.fair_check import FAIRCheck

from pprint import pprint

DEBUG = True
UID = "https://doi.org/10.1594/PANGAEA.902845"
OAIPMH_ENDPOINT = "https://ws.pangaea.de/oai/"


@pytest.fixture(scope="session")
def fair_check() -> FAIRCheck:
    fc = FAIRCheck(uid=UID, oaipmh_endpoint=OAIPMH_ENDPOINT, test_debug=DEBUG)
    assert fc.id == UID
    assert fc.oaipmh_endpoint == OAIPMH_ENDPOINT
    assert fc.metadata_service_url == OAIPMH_ENDPOINT
    assert fc.metadata_service_type == "oai_pmh"
    return fc


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


@pytest.mark.vcr
def test_check_minimal_metatadata(fair_check: FAIRCheck) -> None:
    fair_check.check_minimal_metatadata()


@pytest.mark.vcr
def test_check_data_access_level(fair_check: FAIRCheck) -> None:
    fair_check.check_data_access_level()


@pytest.mark.vcr
def test_check_license(fair_check: FAIRCheck) -> None:
    fair_check.check_license()


@pytest.mark.vcr
def test_check_relatedresources(fair_check: FAIRCheck) -> None:
    fair_check.check_relatedresources()


@pytest.mark.vcr
def test_check_searchable(fair_check: FAIRCheck) -> None:
    fair_check.check_searchable()


@pytest.mark.vcr
def test_check_data_content_metadata(fair_check: FAIRCheck) -> None:
    fair_check.check_data_content_metadata()


@pytest.mark.vcr
def test_check_data_file_format(fair_check: FAIRCheck) -> None:
    fair_check.check_data_file_format()


@pytest.mark.vcr
def test_check_community_metadatastandards(fair_check: FAIRCheck) -> None:
    fair_check.check_community_metadatastandards()


@pytest.mark.vcr
def test_check_data_provenance(fair_check: FAIRCheck) -> None:
    fair_check.check_data_provenance()


@pytest.mark.vcr
def test_check_formal_metadata(fair_check: FAIRCheck) -> None:
    fair_check.check_formal_metadata()


@pytest.mark.vcr
def test_check_semantic_vocabulary(fair_check: FAIRCheck) -> None:
    fair_check.check_semantic_vocabulary()


@pytest.mark.vcr
def test_check_metadata_preservation(fair_check: FAIRCheck) -> None:
    fair_check.check_metadata_preservation()


@pytest.mark.vcr
def test_check_standardised_protocol_metadata(fair_check: FAIRCheck) -> None:
    fair_check.check_standardised_protocol_metadata()


@pytest.mark.vcr
def test_check_standardised_protocol_data(fair_check: FAIRCheck) -> None:
    fair_check.check_standardised_protocol_data()
