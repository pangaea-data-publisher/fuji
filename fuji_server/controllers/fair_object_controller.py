import connexion
from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.models.body import Body  # noqa: E501
from fuji_server.models.fair_results import FAIRResults  # noqa: E501
# MIT License
#
# Copyright (c) 2020 PANGAEA (https://www.pangaea.de/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import datetime

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

        timestmp = datetime.datetime.now().replace(microsecond=0).isoformat()
        metric_spec = Preprocessor.metric_specification
        totalmetrics = len(results)
        final_response = FAIRResults(timestamp= timestmp, metric_specification=metric_spec, total_metrics=totalmetrics, results=results)
    return final_response

