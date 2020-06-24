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
        results = []
        body = Body.from_dict(connexion.request.get_json())  # noqa: E501
        identifier=body.object_identifier
        debug = body.test_debug
        ft = FAIRCheck(uid=identifier, test_debug=debug)

        uid_result, pid_result = ft.check_unique_persistent()
        core_metadata_result = ft.check_minimal_metatadata()
        content_identifier_included_result = ft.check_content_identifier_included()
        check_searchable_result = ft.check_searchable()
        access_result = ft.check_data_access_level()
        relatedresources_result = ft.check_relatedresources()
        license_result = ft.check_license()
        community_standards_result = ft.check_community_metadatastandards()
        ft.check_formal_metadata()

        results.append(uid_result)
        results.append(pid_result)
        results.append(core_metadata_result)
        results.append(content_identifier_included_result)
        results.append(check_searchable_result)
        results.append(access_result)
        results.append(relatedresources_result)
        results.append(license_result)
        results.append(community_standards_result)


    return results

