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
import re

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.data_content_metadata import DataContentMetadata
from fuji_server.models.data_content_metadata_output import DataContentMetadataOutput
from fuji_server.models.data_content_metadata_output_inner import DataContentMetadataOutputInner


class FAIREvaluatorDataContentMetadata(FAIREvaluator):
    """
    A class to evaluate whether the metadata specifies the content of the data (R1.01MD). A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate the metadata that specifies the content of the data, e.g., resource type and links. In addition, the metadata includes
        verifiable data descriptor file info (size and type) and the measured variables observation types will also be evaluated.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-R1-01MD")
        self.data_content_descriptors = []
        self.test_passed = []

    def subtestDataContentInfoGiven(self):
        test_result = False
        test_score = self.getTestConfigScore(self.metric_identifier + "-1b")
        if isinstance(self.fuji.content_identifier, dict):
            if len(self.fuji.content_identifier) > 0:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1b", test_score, "pass")
        return test_result

    def subtestResourceTypeGiven(self):
        test_result = False
        test_score = self.getTestConfigScore(self.metric_identifier + "-1a")
        resource_types = self.fuji.metadata_merged.get("object_type")
        if resource_types:
            if not isinstance(resource_types, list):
                resource_types = [resource_types]
            for resource_type in resource_types:
                resource_type = str(resource_type).lower()
                if str(resource_type).startswith("http"):
                    # http://schema.org/Dataset
                    resource_type = str(resource_type).split("/")[-1]
                if (
                    str(resource_type).lower() in self.fuji.VALID_RESOURCE_TYPES
                    or resource_type in self.fuji.SCHEMA_ORG_CONTEXT
                ):
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        self.metric_identifier
                        + " : Valid resource type (e.g. subtype of schema.org/CreativeWork, DCMI Type  or DataCite resourceType) specified -: {}".format(
                            resource_type
                        ),
                    )
                    self.output.object_type = resource_type
                    self.setEvaluationCriteriumScore(self.metric_identifier + "-1a", test_score, "pass")
                    test_result = True
                else:
                    self.logger.warning(
                        self.metric_identifier
                        + " : Invalid resource type (e.g. subtype of schema.org/CreativeWork, DCMI Type  or DataCite resourceType) specified -: "
                        + str(resource_type)
                    )
        else:
            self.logger.warning(self.metric_identifier + " : NO resource type specified ")
        return test_result

    def testMinimalInformationAboutDataContentAvailable(self):
        test_result = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            if self.subtestResourceTypeGiven():
                test_result = True
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
            if self.subtestDataContentInfoGiven():
                test_result = True
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
            if test_result and self.metric_identifier + "-1" not in self.test_passed:
                self.test_passed.append(self.metric_identifier + "-1")
                self.score.earned += test_score
                self.maturity = self.getTestConfigMaturity(
                    self.metric_identifier + "-1"
                )  # self.metric_tests.get(self.metric_identifier + '-1').metric_test_maturity_config
        return test_result

    def subtestDataTypeAndSizeGiven(self, test_data_content_url):
        test_result = False
        if test_data_content_url:
            data_object = self.fuji.content_identifier.get(test_data_content_url)
            if data_object.get("claimed_type") and data_object.get("claimed_size"):
                test_result = True
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2a", 0, "pass")
                self.logger.log(
                    self.fuji.LOG_SUCCESS, self.metric_identifier + " : Found file size and type specified in metadata"
                )
            elif not data_object.get("claimed_type"):
                self.logger.warning(
                    f"{self.metric_identifier} : NO info about file type available in given metadata -: "
                )
            else:
                self.logger.warning(
                    f"{self.metric_identifier} : NO info about file size available in given metadata -: "
                )
        return test_result

    def subtestMeasuredVariablesGiven(self):
        test_result = False
        if self.fuji.metadata_merged.get("measured_variable"):
            test_result = True
            self.setEvaluationCriteriumScore(self.metric_identifier + "-2b", 0, "pass")
            self.logger.log(
                self.fuji.LOG_SUCCESS,
                self.metric_identifier
                + " : Found measured variables or observations (aka parameters) as content descriptor",
            )
        return test_result

    def testVerifiableDataDescriptorsAvailable(self, test_data_content_url):
        test_result = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            if test_data_content_url:
                if self.subtestDataTypeAndSizeGiven(test_data_content_url):
                    test_result = True
                if self.subtestMeasuredVariablesGiven():
                    test_result = True
            if test_result and self.metric_identifier + "-2" not in self.test_passed:
                self.test_passed.append(self.metric_identifier + "-2")
                self.score.earned += test_score
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-2").metric_test_maturity_config
        return test_result

    def testSizeAndTypeMatchesMetadata(self, test_data_content_url):
        test_result = False
        size_matches = False
        type_matches = False
        if self.isTestDefined(self.metric_identifier + "-3"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-3")
            data_object = self.fuji.content_identifier.get(test_data_content_url)
            if data_object.get("claimed_type") and data_object.get("claimed_size"):
                if not isinstance(data_object.get("tika_content_type"), list):
                    data_object["tika_content_type"] = [data_object.get("tika_content_type")]
                if data_object.get("content_size") and data_object.get("claimed_size"):
                    if data_object.get("truncated") and data_object.get("header_content_size"):
                        self.logger.info(
                            "{} : Since file was truncated will rely on content size given in HTTP header -:  {}".format(
                                self.metric_identifier, str(data_object.get("header_content_size"))
                            )
                        )
                        data_object["content_size"] = data_object.get("header_content_size")
                    try:
                        if data_object.get("claimed_size"):
                            data_size = data_object.get("claimed_size")
                            try:
                                dsm = re.match(r"(\d+(?:\.\d+)?)\s*[A-Za-z]*", str(data_size))
                                if dsm[1]:
                                    data_size = dsm[1]
                            except:
                                pass
                            object_size = int(float(data_size))
                            if object_size == int(float(data_object.get("content_size"))):
                                size_matches = True
                                self.logger.info(
                                    "{} : Sucessfully verified content size from downloaded file -: (expected: {}, found: {})".format(
                                        self.metric_identifier,
                                        str(data_object.get("claimed_size")),
                                        str(data_object.get("content_size")),
                                    )
                                )
                            else:
                                self.logger.warning(
                                    "{} : Could not verify content size from downloaded file -: (expected: {}, found: {})".format(
                                        self.metric_identifier,
                                        str(data_object.get("claimed_size")),
                                        str(data_object.get("content_size")),
                                    )
                                )
                            data_content_filesize_inner = DataContentMetadataOutputInner()
                            data_content_filesize_inner.descriptor = "file size"
                            data_content_filesize_inner.descriptor_value = data_object.get("claimed_size")
                            data_content_filesize_inner.matches_content = size_matches
                            self.data_content_descriptors.append(data_content_filesize_inner)
                    except Exception:
                        self.logger.warning(
                            "{} : Could not verify content size from downloaded file -: (expected: {}, found: {})".format(
                                self.metric_identifier,
                                str(data_object.get("claimed_size")),
                                str(data_object.get("content_size")),
                            )
                        )

                if data_object.get("header_content_type") == data_object.get("claimed_type") or data_object.get(
                    "claimed_type"
                ) in data_object.get("tika_content_type"):
                    type_matches = True
                    self.logger.info(
                        "{} : Sucessfully verified content type from downloaded file -: (expected: {}, found: via tika {})".format(
                            self.metric_identifier,
                            data_object.get("claimed_type"),
                            str(data_object.get("tika_content_type"))
                            + " or via header "
                            + str(data_object.get("header_content_type")),
                        )
                    )
                else:
                    self.logger.warning(
                        "{} : Could not verify content type from downloaded file -: (expected: {}, found: via tika {})".format(
                            self.metric_identifier,
                            data_object.get("claimed_type"),
                            str(data_object.get("tika_content_type"))
                            + " or via header "
                            + str(data_object.get("header_content_type")),
                        )
                    )
                data_content_filetype_inner = DataContentMetadataOutputInner()
                data_content_filetype_inner.descriptor = "file type"
                data_content_filetype_inner.descriptor_value = data_object.get("claimed_type")
                data_content_filetype_inner.matches_content = type_matches
                self.data_content_descriptors.append(data_content_filetype_inner)
            if size_matches and type_matches and self.metric_identifier + "-3" not in self.test_passed:
                self.test_passed.append(self.metric_identifier + "-1")
                self.score.earned += test_score
                self.setEvaluationCriteriumScore(self.metric_identifier + "-3", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-3").metric_test_maturity_config
                test_result = True
        return test_result

    def testVariablesMatchMetadata(self, test_data_content_url):
        test_result = False
        if self.isTestDefined(self.metric_identifier + "-4"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-4")
            test_data_object = self.fuji.content_identifier.get(test_data_content_url)
            if test_data_object:
                if self.fuji.metadata_merged.get("measured_variable"):
                    if not test_data_object.get("test_data_content_text"):
                        self.logger.warning(
                            self.metric_identifier
                            + " : Could not verify measured variables found in data object content, content parsing failed"
                        )
                    for variable in self.fuji.metadata_merged["measured_variable"]:
                        variable_match = False
                        variable_metadata_inner = DataContentMetadataOutputInner()
                        variable_metadata_inner.descriptor = "measured_variable"
                        variable_metadata_inner.descriptor_value = variable
                        if test_data_object.get("test_data_content_text"):
                            if variable in test_data_object.get("test_data_content_text"):
                                test_result = True
                                variable_match = True
                                self.logger.log(
                                    self.fuji.LOG_SUCCESS,
                                    self.metric_identifier
                                    + " : Found specified measured variable in data object content -: "
                                    + str(variable),
                                )
                        variable_metadata_inner.matches_content = variable_match
                        self.data_content_descriptors.append(variable_metadata_inner)
                else:
                    self.logger.warning(
                        "FsF-R1-01MD : NO measured variables found in metadata, skip 'measured_variable' test."
                    )
                if test_result and self.metric_identifier + "-4" not in self.test_passed:
                    self.test_passed.append(self.metric_identifier + "-4")
                    self.score.earned += test_score
                    self.setEvaluationCriteriumScore(self.metric_identifier + "-4", test_score, "pass")
                    self.maturity = self.metric_tests.get(self.metric_identifier + "-4").metric_test_maturity_config
        return test_result

    def evaluate(self):
        self.result = DataContentMetadata(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = DataContentMetadataOutput()
        test_status = "fail"
        self.logger.info(
            self.metric_identifier + f" : Object landing page accessible status -: {self.fuji.isLandingPageAccessible}"
        )

        if self.testMinimalInformationAboutDataContentAvailable():
            test_status = "pass"
        if isinstance(self.fuji.content_identifier, dict):
            if len(self.fuji.content_identifier) > 0:
                verified_urls = [e for e, v in self.fuji.content_identifier.items() if v.get("verified")]
                if verified_urls:
                    test_data_content_urls = verified_urls
                else:
                    test_data_content_urls = list(self.fuji.content_identifier.keys())
                for test_data_content_url in test_data_content_urls:
                    if self.testVerifiableDataDescriptorsAvailable(test_data_content_url):
                        test_status = "pass"
                    if self.testSizeAndTypeMatchesMetadata(test_data_content_url):
                        test_status = "pass"
                    if self.testVariablesMatchMetadata(test_data_content_url):
                        test_status = "pass"
            else:
                self.logger.warning(
                    self.metric_identifier
                    + " : NO data object content available/accessible to perform file descriptors (type and size) tests"
                )

        self.output.data_content_descriptor = self.data_content_descriptors
        self.result.output = self.output
        self.result.score = self.score
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.test_status = test_status
