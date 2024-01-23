# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import datetime

import connexion

from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.models.fair_results import FAIRResults


async def assess_by_id(body):
    """assess_by_id

    Evaluate FAIRness of a data object based on its identifier # noqa: E501

    :param body:
    :type body: dict | bytes

    :rtype: FAIRResults
    """

    allow_remote_logging = False
    if connexion.request.content_type == "application/json":
        # The client has to send this HTTP header (Allow-Remote-Logging:True) explicitely to enable remote logging
        # Useful for e.g. web clients..
        allow_remote_logging = connexion.request.headers.get("Allow-Remote-Logging")
        debug = True
        results = []
        # json_body = await connexion.request.json()
        # body = Body.from_dict(json_body)
        # clienturi = Body.from_dict(connexion.request
        identifier = body.get("object_identifier")
        debug = body.get("test_debug")
        metadata_service_endpoint = body.get("metadata_service_endpoint")
        oaipmh_endpoint = body.get("oaipmh_endpoint")
        metadata_service_type = body.get("metadata_service_type")
        usedatacite = body.get("use_datacite")
        usegithub = body.get("use_github")
        metric_version = body.get("metric_version")
        print("BODY METRIC", metric_version)
        auth_token = body.get("auth_token")
        auth_token_type = body.get("auth_token_type")
        logger = Preprocessor.logger
        # updating re3data
        Preprocessor.retrieve_datacite_re3repos()

        logger.info("Assessment target: " + identifier)
        print("Assessment target: ", identifier, flush=True)
        starttimestmp = datetime.datetime.now().replace(microsecond=0).isoformat() + "Z"
        ft = FAIRCheck(
            uid=identifier,
            test_debug=debug,
            metadata_service_url=metadata_service_endpoint,
            metadata_service_type=metadata_service_type,
            use_datacite=usedatacite,
            use_github=usegithub,
            oaipmh_endpoint=oaipmh_endpoint,
            metric_version=metric_version,
        )
        # dataset level authentication
        if auth_token:
            ft.set_auth_token(auth_token, auth_token_type)
        # set target for remote logging
        remote_log_host, remote_log_path = Preprocessor.remote_log_host, Preprocessor.remote_log_path
        # print(remote_log_host, remote_log_path)
        if remote_log_host and remote_log_path and allow_remote_logging:
            print("Remote logging enabled...")
            if ft.weblogger:
                ft.logger.addHandler(ft.weblogger)
        else:
            print("Remote logging disabled...")
            if ft.weblogger:
                ft.logger.removeHandler(ft.weblogger)

        print("starting harvesting ")
        ft.harvest_all_metadata()
        uid_result, pid_result = ft.check_unique_persistent_metadata_identifier()
        if ft.repeat_pid_check:
            ft.retrieve_metadata_external(ft.pid_url, repeat_mode=True)
        ft.harvest_re3_data()
        ft.harvest_github()
        core_metadata_result = ft.check_minimal_metatadata()
        # print(ft.metadata_unmerged)
        content_identifier_included_result = ft.check_data_identifier_included_in_metadata()
        # print('F-UJI checks: access level')
        access_level_result = ft.check_data_access_level()
        # print('F-UJI checks: license')
        license_result = ft.check_license()
        license_file_result = ft.check_license_file()
        # print('F-UJI checks: related')
        related_resources_result = ft.check_relatedresources()
        # print('F-UJI checks: searchable')
        check_searchable_result = ft.check_searchable()
        # print('F-UJI checks: data content')
        ft.harvest_all_data()
        uid_data_result = ft.check_unique_content_identifier()
        pid_data_result = ft.check_persistent_data_identifier()
        upid_software_result = ft.check_unique_persistent_software_identifier()
        software_component_result = ft.check_software_component_identifier()
        version_identifier_result = ft.check_version_identifier()
        development_metadata_result = ft.check_development_metadata()
        open_api_result = ft.check_open_api()
        requirements_result = ft.check_requirements()
        test_cases_result = ft.check_test_cases()
        data_identifier_included_result = ft.check_data_content_metadata()
        metadata_identifier_included_result = ft.check_metadata_identifier_included_in_metadata()
        data_file_format_result = ft.check_data_file_format()
        # print('F-UJI checks: data file format')
        community_standards_result = ft.check_community_metadatastandards()
        data_provenance_result = ft.check_data_provenance()
        code_provenance_result = ft.check_code_provenance()
        formal_metadata_result = ft.check_formal_metadata()
        # print('F-UJI checks: semantic vocab')
        semantic_vocab_result = ft.check_semantic_vocabulary()
        ft.check_metadata_preservation()
        standard_protocol_data_result = ft.check_standardised_protocol_data()
        standard_protocol_metadata_result = ft.check_standardised_protocol_metadata()
        if uid_result:
            results.append(uid_result)
        if pid_result:
            results.append(pid_result)
        if uid_data_result:
            results.append(uid_data_result)
        if pid_data_result:
            results.append(pid_data_result)
        if upid_software_result:
            results.append(upid_software_result)
        if software_component_result:
            results.append(software_component_result)
        if version_identifier_result:
            results.append(version_identifier_result)
        if development_metadata_result:
            results.append(development_metadata_result)
        if open_api_result:
            results.append(open_api_result)
        if requirements_result:
            results.append(requirements_result)
        if test_cases_result:
            results.append(test_cases_result)
        if core_metadata_result:
            results.append(core_metadata_result)
        if content_identifier_included_result:
            results.append(content_identifier_included_result)
        if check_searchable_result:
            results.append(check_searchable_result)
        if formal_metadata_result:
            results.append(formal_metadata_result)
        if semantic_vocab_result:
            results.append(semantic_vocab_result)
        if related_resources_result:
            results.append(related_resources_result)
        if data_identifier_included_result:
            results.append(data_identifier_included_result)
        if metadata_identifier_included_result:
            results.append(metadata_identifier_included_result)
        if license_result:
            results.append(license_result)
        if license_file_result:
            results.append(license_file_result)
        if access_level_result:
            results.append(access_level_result)
        if data_provenance_result:
            results.append(data_provenance_result)
        if code_provenance_result:
            results.append(code_provenance_result)
        if community_standards_result:
            results.append(community_standards_result)
        if data_file_format_result:
            results.append(data_file_format_result)
        if standard_protocol_data_result:
            results.append(standard_protocol_data_result)
        if standard_protocol_metadata_result:
            results.append(standard_protocol_metadata_result)
        debug_messages = ft.get_log_messages_dict()
        # ft.logger_message_stream.flush()
        summary = ft.get_assessment_summary(results)
        for res_k, res_v in enumerate(results):
            if ft.isDebug:
                debug_list = debug_messages.get(res_v["metric_identifier"])
                # debug_list= ft.msg_filter.getMessage(res_v['metric_identifier'])
                if debug_list is not None:
                    results[res_k]["test_debug"] = debug_messages.get(res_v["metric_identifier"])
                else:
                    results[res_k]["test_debug"] = ["INFO: No debug messages received"]
            else:
                results[res_k]["test_debug"] = ["INFO: Debugging disabled"]
                debug_messages = {}
        if len(ft.logger.handlers) > 1:
            ft.logger.handlers = [ft.logger.handlers[-1]]
        # endtimestmp = datetime.datetime.now().replace(microsecond=0).isoformat()
        endtimestmp = (
            datetime.datetime.now().replace(microsecond=0).isoformat() + "Z"
        )  # use timestamp format from RFC 3339 as specified in openapi3
        metric_spec = ft.metric_helper.metric_specification
        resolved_url = ft.landing_url
        if not resolved_url:
            resolved_url = "not defined"
        # metric_version = os.path.basename(Preprocessor.METRIC_YML_PATH)
        totalmetrics = len(results)
        request = body
        if ft.pid_url:
            idhelper = IdentifierHelper(ft.pid_url)
            request["normalized_object_identifier"] = idhelper.get_normalized_id()
        final_response = FAIRResults(
            request=request,
            start_timestamp=starttimestmp,
            end_timestamp=endtimestmp,
            software_version=ft.FUJI_VERSION,
            test_id=ft.test_id,
            metric_version=metric_version,
            metric_specification=metric_spec,
            total_metrics=totalmetrics,
            results=results,
            summary=summary,
            resolved_url=resolved_url,
        )
    return final_response
