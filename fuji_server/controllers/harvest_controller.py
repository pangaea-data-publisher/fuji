import connexion
import six

# -*- coding: utf-8 -*-
################################################################################
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
################################################################################

import datetime
import os
import connexion
from fuji_server.controllers.fair_check import FAIRCheck
from fuji_server.helper.preprocessor import Preprocessor

from fuji_server.models.harvest import Harvest  # noqa: E501
from fuji_server.models.harvest_results import HarvestResults  # noqa: E501
from fuji_server.models.harvest_results_metadata import HarvestResultsMetadata  # noqa: E501
from fuji_server import util


def harvest_by_id(body=None):  # noqa: E501
    """harvest_by_id

    Harvest metadata of a data object based on its identifier # noqa: E501

    :param body: 
    :type body: dict | bytes

    :rtype: HarvestResults
    """
    if connexion.request.is_json:
        body = Harvest.from_dict(connexion.request.get_json())  # noqa: E501
        identifier = body.object_identifier
        logger = Preprocessor.logger
        ft = FAIRCheck(uid=identifier,
                       test_debug=False,
                       metadata_service_url=None,
                       metadata_service_type=None,
                       use_datacite=False,
                       oaipmh_endpoint=None)
        ft.harvest_all_metadata()

        ft.check_unique_persistent()
        if ft.repeat_pid_check:
            ft.retrieve_metadata_external_xml_negotiated([ft.pid_url])
            ft.retrieve_metadata_external_schemaorg_negotiated([ft.pid_url])
            ft.retrieve_metadata_external_rdf_negotiated([ft.pid_url])
            ft.retrieve_metadata_external_datacite()
            print(type(ft.metadata_unmerged))

        harvest_result =[]
        for metadata in ft.metadata_unmerged:
            harvest_result.append(HarvestResultsMetadata(
                metadata.get('method'),
                metadata.get('url'),
                metadata.get('format'),
                metadata.get('schema'),
                metadata.get('namespaces'),
                metadata.get('metadata')
            ))
        response = HarvestResults(identifier, harvest_result)
        #response

    return response
