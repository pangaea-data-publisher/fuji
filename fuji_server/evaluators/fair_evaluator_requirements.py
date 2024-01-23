# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.requirements import Requirements
from fuji_server.models.requirements_output import RequirementsOutput


class FAIREvaluatorRequirements(FAIREvaluator):
    """
    A class to evaluate whether the software describes what is required to use it (FRSM-13). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate machine-readable information that helps support the understanding of how the software is to be used.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        metric = "FRSM-13-R1"
        self.set_metric(metric)

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testBuildInstructions": ["FRSM-13-R1-1"],
            "testDependencies": ["FRSM-13-R1-2"],
            "testDependenciesBuildAutomatedChecks": ["FRSM-13-R1-CESSDA-1"],
            "testBadgeIncluded": ["FRSM-13-R1-CESSDA-2"],
            "testBuildBadgeStatus": ["FRSM-13-R1-CESSDA-3"],
        }

    def testBuildInstructions(self):
        """The software has build, installation and/or execution instructions.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testBuildInstructions"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for build, installation and execution instructions is not implemented."
            )
            test_requirements = self.metric_tests[test_id].metric_test_requirements
            print(test_requirements)  # list
            # TODO: check each location (if available from harvest) for keywords
        return test_status

    def testDependencies(self):
        """Dependencies are provided in a machine-readable format and the building and installation of the software is automated.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testDependencies"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for dependencies is not implemented.")
        return test_status

    def testDependenciesBuildAutomatedChecks(self):
        """Dependency information and build instructions are included in the README file.
        Linting and other relevant checks are present in the automated build and test process (e.g. via the Jenkinsfile).

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testDependenciesBuildAutomatedChecks"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for dependency information, build instructions and automated checks is not implemented."
            )
        return test_status

    def testBadgeIncluded(self):
        """The README file includes a badge that links to the automated build tool (Jenkins).
        Deployment to development and staging environments is automated (conditional on test results).

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testBadgeIncluded"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for presence of build badge is not implemented.")
        return test_status

    def testBuildBadgeStatus(self):
        """The build badge indicates the status of the latest build (passing or failing).

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testBuildBadgeStatus"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for build badge status is not implemented.")
        return test_status

    def evaluate(self):
        if self.metric_identifier in self.metrics:
            self.result = Requirements(
                id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
            )
            self.output = RequirementsOutput()
            self.result.test_status = "fail"
            if self.testBuildInstructions():
                self.result.test_status = "pass"
            if self.testDependencies():
                self.result.test_status = "pass"
            if self.testDependenciesBuildAutomatedChecks():
                self.result.test_status = "pass"
            if self.testBadgeIncluded():
                self.result.test_status = "pass"
            if self.testBuildBadgeStatus():
                self.result.test_status = "pass"
            else:
                self.result.test_status = "fail"
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the software requirements.")
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
