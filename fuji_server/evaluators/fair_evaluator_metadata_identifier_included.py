# -*- coding: utf-8 -*-

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
import enum
import socket
import urllib

import requests

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.identifier_included import IdentifierIncluded
from fuji_server.models.identifier_included_output import IdentifierIncludedOutput
from fuji_server.models.identifier_included_output_inner import IdentifierIncludedOutputInner


class FAIREvaluatorMetadataIdentifierIncluded(FAIREvaluator):
    """
    A class to evaluate whether the metadata includes the identifier of the data is being described (F3-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the metadata contains an identifier, e.g., PID or URL, which indicates the location of the downloadable data content or
        a data identifier that matches the identifier as part of the assessment request.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-F3-02M")
        self.content_list = []

    def testMetadataUrlOrPIDAvailable(self, datainfolist):
        test_result = False
        object_identifier = []
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            if datainfolist:
                for datainfo in datainfolist:
                    if isinstance(datainfo, dict):
                        method = datainfo.get("method")
                        if datainfo.get("metadata"):
                            object_identifier = datainfo["metadata"].get("object_identifier")
                            if isinstance(object_identifier, str):
                                object_identifier = [object_identifier]
                        if object_identifier:
                            for oid in object_identifier:
                                if oid and oid in [self.fuji.landing_url, self.fuji.id, self.fuji.pid_url]:
                                    test_result = True
                                    self.content_list.append(oid)
                                    self.logger.info(
                                        self.metric_identifier
                                        + " : Found metadata identifier in metadata -: {} via {}".format(oid, method)
                                    )
            if test_result:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-1").metric_test_maturity_config
                self.score.earned += test_score
        return test_result

    def evaluate(self):
        number_of_contents = 0
        self.result = IdentifierIncluded(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = IdentifierIncludedOutput()
        contents = self.fuji.metadata_unmerged
        # print(self.fuji.metadata_unmerged)
        self.result.test_status = "fail"

        if self.testMetadataUrlOrPIDAvailable(contents):
            self.result.test_status = "pass"

        if self.result.test_status == "pass":
            self.logger.log(
                self.fuji.LOG_SUCCESS,
                self.metric_identifier
                + " : Number of object content identifier found -: {}".format(number_of_contents),
            )
        else:
            self.logger.warning(self.metric_identifier + " : Valid data (content) identifier missing.")

        self.result.metric_tests = self.metric_tests
        self.output.object_content_identifier_included = self.content_list
        self.result.output = self.output
        self.result.maturity = self.maturity
        self.result.score = self.score
