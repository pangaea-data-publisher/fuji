# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.api import API
from fuji_server.models.api_output import APIOutput


class FAIREvaluatorAPI(FAIREvaluator):
    """
    A class to evaluate whether the software uses open APIs that support machine-readable interface definition (FRSM-11). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the API is documented, open and machine-readable.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        metric = "FRSM-11-I1"
        self.set_metric(metric)

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testDocumented": ["FRSM-11-I1-1"],
            "testOpen": ["FRSM-11-I1-2"],
            "testMachineReadable": ["FRSM-11-I1-3"],
            "testCESSDAGuidelines": ["FRSM-11-I1-CESSDA-1"],
            "testOpenAPIStandard": ["FRSM-11-I1-CESSDA-2"],
            "testPublishedCESSDA": ["FRSM-11-I1-CESSDA-3"],
        }

    def testDocumented(self):
        """The software provides documented APIs.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testDocumented"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for documented API is not implemented.")
        return test_status

    def testOpen(self):
        """The APIs are open (freely accessible).

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testOpen"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for openness of API is not implemented.")
        return test_status

    def testMachineReadable(self):
        """The APIs include a machine-readable interface definition.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testMachineReadable"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for machine-readable interface definition is not implemented."
            )
        return test_status

    def testCESSDAGuidelines(self):
        """The API meets SML3 of the CESSDA Development Documentation guidelines,
        i.e. there is external documentation that describes all API functionality,
        which is sufficient to be used by any developer.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testCESSDAGuidelines"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for CESSDA guidelines is not implemented.")
        return test_status

    def testOpenAPIStandard(self):
        """The software's REST APIs comply with the OpenAPI standard.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testOpenAPIStandard"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for Open API standard compliance is not implemented.")
        return test_status

    def testPublishedCESSDA(self):
        """The software's REST APIs are described in the published CESSDA API definitions.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testPublishedCESSDA"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for description in CESSDA API definition is not implemented."
            )
        return test_status

    def evaluate(self):
        if self.metric_identifier in self.metrics:
            self.result = API(
                id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
            )
            self.output = APIOutput()
            self.result.test_status = "fail"
            if self.testDocumented():
                self.result.test_status = "pass"
            if self.testOpen():
                self.result.test_status = "pass"
            if self.testMachineReadable():
                self.result.test_status = "pass"
            if self.testCESSDAGuidelines():
                self.result.test_status = "pass"
            if self.testOpenAPIStandard():
                self.result.test_status = "pass"
            if self.testPublishedCESSDA():
                self.result.test_status = "pass"
            else:
                self.result.test_status = "fail"
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the software API.")
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
