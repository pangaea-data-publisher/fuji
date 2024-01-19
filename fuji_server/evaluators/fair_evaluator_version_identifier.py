# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.models.uniqueness_output import UniquenessOutput


class FAIREvaluatorVersionIdentifier(FAIREvaluator):
    """
    A class to evaluate whether each version of the software has a unique identifier (FRSM-03). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether each software identifier resolves to a different version and examine identifier metadata.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        metric = "FRSM-03-F1.2"
        self.set_metric(metric)

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testDistinctIdentifiers": ["FRSM-03-F1.2-1"],
            "testIdentifierMetadata": ["FRSM-03-F1.2-2"],
            "testVersionNumber": ["FRSM-03-F1.2-3"],
            "testZenodoPublication": ["FRSM-03-F1.2-CESSDA-1"],
            "testReleaseChecklistDocker": ["FRSM-03-F1.2-CESSDA-2"],
            "testReservedDOI": ["FRSM-03-F1.2-CESSDA-3"],
        }

    def testDistinctIdentifiers(self):
        """Each version of the software has a different identifier.

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
        """Relations between the versions are included in the identifier metadata.

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

    def testVersionNumber(self):
        """The version number is included in the identifier metadata.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testVersionNumber"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for version number in identifier is not implemented.")
        return test_status

    def testZenodoPublication(self):
        """Each release is published to Zenodo and a DOI obtained.
        A publication consists of a release tarball matching the release tag in the repository.
        Release tags exist and adhere to SemVer 2.0.0.
        The README and CHANGELOG must be up to date prior to release and they must be added to the
        Zenodo record in addition to the tarball.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testZenodoPublication"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for Zenodo publication is not implemented.")
        return test_status

    def testReleaseChecklistDocker(self):
        """A release checklist is used to ensure that all necessary steps are taken for each release.
        Releases must be available as Docker images with the release version as tag.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testReleaseChecklistDocker"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for release checklist and Docker image is not implemented."
            )
        return test_status

    def testReservedDOI(self):
        """Reserve the DOI in Zenodo, prior to release, to avoid a circularity problem with the CHANGELOG and the tarball.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testReservedDOI"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for reserved DOIs is not implemented.")
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
            if self.testVersionNumber():
                self.result.test_status = "pass"
            if self.testZenodoPublication():
                self.result.test_status = "pass"
            if self.testReleaseChecklistDocker():
                self.result.test_status = "pass"
            if self.testReservedDOI():
                self.result.test_status = "pass"
            else:
                self.result.test_status = "fail"
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the software version identifier.")
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
