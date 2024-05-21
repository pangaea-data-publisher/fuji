# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from urllib.parse import urlparse

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.standardised_protocol_data import StandardisedProtocolData
from fuji_server.models.standardised_protocol_data_output import StandardisedProtocolDataOutput


class FAIREvaluatorStandardisedProtocolData(FAIREvaluator):
    """
    A class to evaluate whether the data is accessible through a standardized communication protocol (A1-03D).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate the accesibility of the data on whether the URI's scheme is based on
        a shared application protocol.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FsF-A1-03D", "FRSM-09-A1"])
        self.data_output = {}

        self.metric_test_map = {  # overall map
            "testStandardProtocolDataUsed": ["FsF-A1-03D-1", "FRSM-09-A1-1", "FRSM-09-A1-CESSDA-1"],
            "testAuth": ["FRSM-09-A1-2", "FRSM-09-A1-CESSDA-2"],
            "testPRs": ["FRSM-09-A1-CESSDA-3"],
        }

    def testStandardProtocolDataUsed(self):
        agnostic_test_name = "testStandardProtocolDataUsed"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        # TODO implement
        if test_id.startswith("FRSM"):
            self.logger.warning(f"{self.metric_identifier} : Test for standard protocol is not implemented for FRSM.")
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            content_identifiers = self.fuji.content_identifier.values()
            if content_identifiers:
                if len(content_identifiers) > 0:
                    # here we only test the first content identifier
                    for data_link in content_identifiers:
                        data_url = data_link.get("url")
                        if data_url:
                            data_parsed_url = urlparse(data_url)
                            data_url_scheme = data_parsed_url.scheme
                            if data_url_scheme in self.fuji.STANDARD_PROTOCOLS:
                                self.logger.log(
                                    self.fuji.LOG_SUCCESS,
                                    self.metric_identifier
                                    + " : Standard protocol for access to data object found -: "
                                    + data_url_scheme,
                                )
                                self.data_output = {data_url_scheme: self.fuji.STANDARD_PROTOCOLS.get(data_url_scheme)}
                                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                                self.maturity = self.getTestConfigMaturity(test_id)
                                test_status = True
                                self.score.earned = test_score
                                break
            else:
                self.logger.warning(
                    self.metric_identifier
                    + " : Skipping protocol test for data since NO content (data) identifier is given in metadata"
                )
        return test_status

    def testAuth(self):
        """If authentication or authorisation are required, these are supported by the communication protocols and the repository / forge.
        CESSDA: No authentication is required to view and/or clone CESSDA's public repositories, even so, their contents cannot be modified directly by 3rd parties.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testAuth"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for authentication and authorisation is not implemented."
            )
        return test_status

    def testPRs(self):
        """Pull requests are used to propose modifications to the contents.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testPRs"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for usage of PRs is not implemented.")
        return test_status

    def evaluate(self):
        self.result = StandardisedProtocolData(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )

        test_status = "fail"
        if self.testStandardProtocolDataUsed():
            test_status = "pass"
        self.result.score = self.score
        self.result.output = StandardisedProtocolDataOutput(standard_data_protocol=self.data_output)
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.test_status = test_status
