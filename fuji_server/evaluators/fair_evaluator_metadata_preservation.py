# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.metadata_preserved import MetadataPreserved
from fuji_server.models.metadata_preserved_output import MetadataPreservedOutput


class FAIREvaluatorMetadataPreserved(FAIREvaluator):
    """
    A class to evaluate that the metadata remains available, even if the data is no longer available (A2-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()

    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FsF-A2-01M", "FRSM-08-F4"])

        self.metric_test_map = {  # overall map
            "testPreservationGuaranteed": ["FsF-A2-01M-1", "FRSM-08-F4-1"],
            "testPublicSearchEngine": ["FRSM-08-F4-2", "FRSM-08-F4-CESSDA-2"],
            "testMultipleCrossReferenced": ["FRSM-08-F4-3", "FRSM-08-F4-CESSDA-3"],
            "testZenodoLandingPage": ["FRSM-08-F4-CESSDA-1"],
        }

    def testPreservationGuaranteed(self):
        agnostic_test_name = "testPreservationGuaranteed"
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        test_status = False
        if test_defined:
            # TODO implement
            if test_id.startswith("FRSM"):
                self.logger.warning(
                    f"{self.metric_identifier} : Test for descriptive metadata is not implemented for FRSM."
                )
            registry_bound_pid = ["doi"]
            test_score = self.getTestConfigScore(test_id)
            if self.fuji.pid_scheme:
                if self.fuji.pid_scheme in registry_bound_pid:
                    test_status = True
                    self.score.earned += test_score
                    self.outputs.append(MetadataPreservedOutput(metadata_preservation_method="datacite"))
                    self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                    self.maturity = self.getTestConfigMaturity(test_id)
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        "{0} : Metadata registry bound PID system used: "
                        + self.fuji.pid_scheme.format(self.metric_identifier),
                    )
                else:
                    self.logger.warning(f"{self.metric_identifier} : NO metadata registry bound PID system used")
        return test_status

    def testPublicSearchEngine(self):
        """The persistent metadata record is available through public search engines. The metadata has a globally unique and persistent identifier.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testPublicSearchEngine"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for availability through public search engine is not implemented."
            )
        return test_status

    def testMultipleCrossReferenced(self):
        """The persistent metadata record is available through multiple, cross-referenced infrastructures.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testMultipleCrossReferenced"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for availability through multiple, cross-referenced infrastructures is not implemented."
            )
        return test_status

    def testZenodoLandingPage(self):
        """The DOI resolves to a Zenodo landing page for the latest release, and metadata can be accessed via the Zenodo API.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testZenodoLandingPage"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for availability through Zenodo (landing page + API) is not implemented."
            )
        return test_status

    def evaluate(self):
        self.result = MetadataPreserved(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.outputs = []  # list of MetadataPreservedOutput

        test_status = "fail"
        if self.testPreservationGuaranteed():
            test_status = "pass"
        if self.testPublicSearchEngine():
            test_status = "pass"
        if self.testMultipleCrossReferenced():
            test_status = "pass"
        if self.testZenodoLandingPage():
            test_status = "pass"

        self.result.score = self.score
        self.result.output = self.outputs
        self.result.metric_tests = self.metric_tests
        self.result.test_status = test_status
        self.result.maturity = self.maturity
