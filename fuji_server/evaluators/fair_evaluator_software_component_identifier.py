# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.models.uniqueness_output import UniquenessOutput


class FAIREvaluatorSoftwareComponentIdentifier(FAIREvaluator):
    """
    A class to evaluate whether different components of the software have their own identifiers (FRSM-02). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the software is assigned to a unique and persistent identifier.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        metric = "FRSM-02-F1.1"
        self.set_metric(metric)

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testDistinctIdentifiers": ["FRSM-02-F1.1-1"],
            "testIdentifierMetadata": ["FRSM-02-F1.1-2"],
            "testModule": ["FRSM-02-F1.1-3"],
            "testSeparateRepositories": ["FRSM-02-F1.1-CESSDA-1"],
            "testComponentZenodoDOI": ["FRSM-02-F1.1-CESSDA-2"],
            "testZenodoTags": ["FRSM-02-F1.1-CESSDA-3"],
        }

    def testDistinctIdentifiers(self):
        """Where the 'software' consists of multiple distinct components, each component has a distinct identifier.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testDistinctIdentifiers"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for distinct identifiers is not implemented.")
        return test_status

    def testIdentifierMetadata(self):
        """The relationship between components is embodied in the identifier metadata.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testIdentifierMetadata"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for identifier metadata is not implemented.")
        return test_status

    def testModule(self):
        """Every component to granularity level GL3 (module) has its own unique identifier.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testModule"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for GL3 (module) identifiers is not implemented.")
        return test_status

    def testSeparateRepositories(self):
        """A separate Git repository is used for the source code of each component (aka microservices).
        The product deployment scripts assemble the constituent components.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testSeparateRepositories"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for separate repositories is not implemented.")
        return test_status

    def testComponentZenodoDOI(self):
        """Each component is deposited in Zenodo with its own DOI.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testComponentZenodoDOI"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for component DOI on Zenodo is not implemented.")
        return test_status

    def testZenodoTags(self):
        """The Zenodo record for each component is tagged with the product(s) that it contributes to.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testZenodoTags"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for Zenodo DOI tags of components is not implemented."
            )
        return test_status

    def evaluate(self):
        if self.metric_identifier in self.metrics:
            self.result = Uniqueness(
                id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
            )
            self.output = UniquenessOutput()
            self.result.test_status = "fail"
            if self.testDistinctIdentifiers():
                self.result.test_status = "pass"
            if self.testIdentifierMetadata():
                self.result.test_status = "pass"
            if self.testModule():
                self.result.test_status = "pass"
            if self.testSeparateRepositories():
                self.result.test_status = "pass"
            if self.testComponentZenodoDOI():
                self.result.test_status = "pass"
            if self.testZenodoTags():
                self.result.test_status = "pass"
            else:
                self.result.test_status = "fail"
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the software component identifiers.")
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
