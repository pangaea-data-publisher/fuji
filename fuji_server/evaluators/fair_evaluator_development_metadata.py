# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.models.uniqueness_output import UniquenessOutput


class FAIREvaluatorDevelopmentMetadata(FAIREvaluator):
    """
    A class to evaluate whether the software includes development metadata which helps define its status (FRSM-05). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the software has machine-readable descriptive metadata associated with it that describes its development and status.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        metric = "FRSM-05-R1"
        self.set_metric(metric)

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testContactInformation": ["FRSM-05-R1-1"],
            "testDevelopmentStatus": ["FRSM-05-R1-2"],
            "testMetadataFormat": ["FRSM-05-R1-3"],
            "testReadme": ["FRSM-05-R1-CESSDA-1"],
            "testVersionNumbering": ["FRSM-05-R1-CESSDA-2"],
        }

    def testContactInformation(self):
        """The software includes metadata for contact or support in the README or other intrinsic metadata file according to community standards.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testContactInformation"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for contact information is not implemented.")
        return test_status

    def testDevelopmentStatus(self):
        """The software includes metadata for development status, links to documentation.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testDevelopmentStatus"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for development status in metadata is not implemented."
            )
        return test_status

    def testMetadataFormat(self):
        """The metadata is contained in a format such as CodeMeta or ProjectObjectModel that enables full machine-actionability.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testMetadataFormat"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for metadata format is not implemented.")
        return test_status

    def testReadme(self):
        """The README and CHANGELOG must be up to date.
        he README contains release details, version details, links to documentation as described in the EURISE Network Technical Reference.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testReadme"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for README information is not implemented.")
        return test_status

    def testVersionNumbering(self):
        """Version numbering follows Semantic Versioning 2.0.0 and pre-release versions may be denoted by appending a hyphen and a series of dot separated identifiers immediately following the patch version.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testVersionNumbering"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for version numbering format is not implemented.")
        return test_status

    def evaluate(self):
        if self.metric_identifier in self.metrics:
            self.result = Uniqueness(
                id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
            )
            self.output = UniquenessOutput()
            self.result.test_status = "fail"
            if self.testContactInformation():
                self.result.test_status = "pass"
            if self.testDevelopmentStatus():
                self.result.test_status = "pass"
            if self.testMetadataFormat():
                self.result.test_status = "pass"
            if self.testReadme():
                self.result.test_status = "pass"
            if self.testVersionNumbering():
                self.result.test_status = "pass"
            else:
                self.result.test_status = "fail"
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the software development metadata.")
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
