# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.code_provenance import CodeProvenance
from fuji_server.models.code_provenance_output import CodeProvenanceOutput


class FAIREvaluatorCodeProvenance(FAIREvaluator):
    """
    A class to evaluate metadata that includes provenance information about code creation (FRSM-17-R1.2).
    A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate the provenance information such as commits
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FRSM-17-R1.2"])

        self.metric_test_map = {  # overall map
            "testCommitHistory": ["FRSM-17-R1.2-1", "FRSM-17-R1.2-CESSDA-1"],
            "testCommitLinkedToIssue": ["FRSM-17-R1.2-2"],
            "testOtherProvenanceTools": ["FRSM-17-R1.2-3"],
            "testIssueLinkedToBranch": ["FRSM-17-R1.2-CESSDA-2"],
            "testPRLinkedToIssue": ["FRSM-17-R1.2-CESSDA-3"],
        }

    def testCommitHistory(self):
        """The software source code repository / forge includes a commit history.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testCommitHistory"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for commit history is not implemented.")
        return test_status

    def testCommitLinkedToIssue(self):
        """The software source code repository links commits to issues / tickets.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testCommitLinkedToIssue"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for commit linkage to issues is not implemented.")
        return test_status

    def testOtherProvenanceTools(self):
        """The software project uses other tools to capture detailed machine readable provenance information.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testOtherProvenanceTools"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for other tools capturing provenance information is not implemented."
            )
        return test_status

    def testIssueLinkedToBranch(self):
        """Code that addresses an issue is developed in a branch prefixed with the issue number.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testIssueLinkedToBranch"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for issue code on branches is not implemented.")
        return test_status

    def testPRLinkedToIssue(self):
        """Links to Pull Requests are included in issue tracker tickets.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testPRLinkedToIssue"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for issues linked to PRs is not implemented.")
        return test_status

    def evaluate(self):
        self.result = CodeProvenance(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = CodeProvenanceOutput()

        provenance_status = "fail"
        if self.testCommitHistory():
            provenance_status = "pass"
        if self.testCommitLinkedToIssue():
            provenance_status = "pass"
        if self.testOtherProvenanceTools():
            provenance_status = "pass"
        if self.testIssueLinkedToBranch():
            provenance_status = "pass"
        if self.testPRLinkedToIssue():
            provenance_status = "pass"

        self.result.test_status = provenance_status
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = self.output
        self.result.score = self.score
