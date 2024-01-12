# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import connexion

from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.models.harvest_results import HarvestResults
from fuji_server.models.harvest_results_metadata import HarvestResultsMetadata


def harvest_by_id(body=None):
    """harvest_by_id

    Harvest metadata of a data object based on its identifier # noqa: E501

    :param body:
    :type body: dict | bytes

    :rtype: HarvestResults
    """
    if connexion.request.content_type == "application/json":
        # body = Harvest.from_dict(connexion.request.get_json())
        identifier = body.get("object_identifier")
        auth_token = body.get("auth_token")
        auth_token_type = body.get("auth_token_type")
        ft = FAIRCheck(
            uid=identifier,
            test_debug=False,
            metadata_service_url=None,
            metadata_service_type=None,
            use_datacite=False,
            oaipmh_endpoint=None,
        )

        # dataset level authentication
        if auth_token:
            ft.set_auth_token(auth_token, auth_token_type)
        ft.harvest_all_metadata()

        ft.check_unique_persistent_metadata_identifier()
        if ft.repeat_pid_check:
            ft.retrieve_metadata_external_xml_negotiated([ft.pid_url])
            ft.retrieve_metadata_external_schemaorg_negotiated([ft.pid_url])
            ft.retrieve_metadata_external_rdf_negotiated([ft.pid_url])
            ft.retrieve_metadata_external_datacite()

        harvest_result = []
        for metadata in ft.metadata_unmerged:
            harvest_result.append(
                HarvestResultsMetadata(
                    metadata.get("offering_method"),
                    metadata.get("url"),
                    metadata.get("format"),
                    metadata.get("schema"),
                    metadata.get("namespaces"),
                    metadata.get("metadata"),
                )
            )
        response = HarvestResults(identifier, harvest_result)

    return response
