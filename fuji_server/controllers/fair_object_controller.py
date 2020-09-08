import connexion
from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.models.body import Body  # noqa: E501
from fuji_server.models.fair_results import FAIRResults  # noqa: E501


def assess_by_id(body):  # noqa: E501
    """assess_by_id

    Evaluate FAIRness of a data object based on its identifier # noqa: E501

    :param body: 
    :type body: dict | bytes

    :rtype: FAIRResults
    """

    if connexion.request.is_json:
        debug = True
        results = []
        body = Body.from_dict(connexion.request.get_json())
        identifier=body.object_identifier
        debug = body.test_debug
        oai = body.oaipmh_endpoint
        ft = FAIRCheck(uid=identifier, test_debug=debug, oaipmh=oai)

        uid_result, pid_result = ft.check_unique_persistent()
        core_metadata_result = ft.check_minimal_metatadata()
        content_identifier_included_result = ft.check_content_identifier_included()
        check_searchable_result = ft.check_searchable()
        access_result = ft.check_data_access_level()
        formal_metadata_result = ft.check_formal_metadata()
        semantic_vocab_result = ft.check_semantic_vocabulary()
        relatedresources_result = ft.check_relatedresources()
        datacontent_result = ft.check_data_content_metadata()
        license_result = ft.check_license()
        provenance_result = ft.check_data_provenance()
        community_standards_result = ft.check_community_metadatastandards()
        fileformat_result = ft.check_data_file_format()

        results.append(uid_result)
        results.append(pid_result)
        results.append(core_metadata_result)
        results.append(content_identifier_included_result)
        results.append(check_searchable_result)
        results.append(access_result)
        results.append(formal_metadata_result)
        results.append(semantic_vocab_result)
        results.append(relatedresources_result)
        results.append(datacontent_result)
        results.append(license_result)
        results.append(provenance_result)
        results.append(community_standards_result)
        results.append(fileformat_result)

    return results

