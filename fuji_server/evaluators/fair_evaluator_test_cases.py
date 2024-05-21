# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.test_case import TestCase
from fuji_server.models.test_case_output import TestCaseOutput


class FAIREvaluatorTestCases(FAIREvaluator):
    """
    A class to evaluate whether the software comes with test cases to demonstrate it is working (FRSM-14). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate automated tests.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        metric = "FRSM-14-R1"
        self.set_metric(metric)

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testPresence": ["FRSM-14-R1-1"],
            "testUnitSystem": ["FRSM-14-R1-2"],
            "testCoverage": ["FRSM-14-R1-3"],
            "testBadges": ["FRSM-14-R1-CESSDA-1"],
            "testProductionVerified": ["FRSM-14-R1-CESSDA-2"],
            "testBadgeStatus": ["FRSM-14-R1-CESSDA-3"],
        }

    def testPresence(self):
        """Tests and data are provided to check that the software is operating as expected.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testPresence"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for presence of tests and test data is not implemented."
            )
        return test_status

    def testUnitSystem(self):
        """Automated unit and system tests are provided.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testUnitSystem"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for Automated unit and system tests is not implemented."
            )
        return test_status

    def testCoverage(self):
        """Code coverage / test coverage is reported.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testCoverage"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for code coverage is not implemented.")
        return test_status

    def testBadges(self):
        """The README file includes badges that link to a comprehensive code quality assessment tool (SonarQube)
        and automated build tool (Jenkins).

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testBadges"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for code quality badges is not implemented.")
        return test_status

    def testProductionVerified(self):
        """A production system has been tested and validated through successful use of the application.
        Compliance with open or internationally recognised standards for the software and software development process
        is evident and documented, and verified through testing of all components.
        Ideally independent verification is documented through regular testing and certification from an independent group.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testProductionVerified"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for verified compliance of production system is not implemented."
            )
        return test_status

    def testBadgeStatus(self):
        """The README file badges indicate the status of the tests and other code quality metrics.
        The repository contains a subdirectory containing code for the test cases that are run automatically.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testBadgeStatus"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for badge status is not implemented.")
        return test_status

    def evaluate(self):
        if self.metric_identifier in self.metrics:
            self.result = TestCase(
                id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
            )
            self.output = TestCaseOutput()
            self.result.test_status = "fail"
            if self.testPresence():
                self.result.test_status = "pass"
            if self.testUnitSystem():
                self.result.test_status = "pass"
            if self.testCoverage():
                self.result.test_status = "pass"
            if self.testBadges():
                self.result.test_status = "pass"
            if self.testProductionVerified():
                self.result.test_status = "pass"
            if self.testBadgeStatus():
                self.result.test_status = "pass"
            else:
                self.result.test_status = "fail"
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the software version identifier.")
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
