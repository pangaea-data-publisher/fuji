# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.models.related_resource import RelatedResource
from fuji_server.models.related_resource_output import RelatedResourceOutput


class FAIREvaluatorRelatedResources(FAIREvaluator):
    """
    A class to evaluate that the metadata links between the data and its related entities (I3-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate the links between metadata whether they relate explicitly in metadata and
        they relate by machine-readable links/identifier.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FsF-I3-01M", "FRSM-12-I2"])
        self.metric_test_map = {  # overall map
            "testRelatedResourcesAvailable": ["FsF-I3-01M-1"],
            "testRelatedResourcesMachineReadable": ["FsF-I3-01M-2", "FRSM-12-I2-1"],
        }
        self.is_actionable = False

    def testRelatedResourcesAvailable(self):
        agnostic_test_name = "testRelatedResourcesAvailable"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            if self.fuji.related_resources:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier
                    + " : Number of related resources found in metadata -: "
                    + str(len(self.fuji.related_resources)),
                )
                test_status = True
                self.output = self.fuji.related_resources
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned = self.total_score
                self.maturity = self.getTestConfigMaturity(test_id)
            else:
                self.logger.warning(
                    self.metric_identifier + " : Could not identify qualified related resources in metadata"
                )
        return test_status

    def testRelatedResourcesMachineReadable(self):
        agnostic_test_name = "testRelatedResourcesMachineReadable"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        # TODO implement
        if test_id.startswith("FRSM"):
            self.logger.warning(
                f"{self.metric_identifier} : Test for machine-readable related resources is not implemented for FRSM."
            )
        if test_defined:
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            if self.fuji.related_resources:
                for relation in self.fuji.related_resources:
                    if isinstance(relation.get("related_resource"), list):
                        relation["related_resource"] = relation.get("related_resource")[0]
                    relation_identifier = IdentifierHelper(relation.get("related_resource"))
                    if relation_identifier.is_persistent or "url" in relation_identifier.identifier_schemes:
                        test_status = True
            if test_status:
                self.score.earned = self.total_score
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + "-2")
        return test_status

    def evaluate(self):
        self.result = RelatedResource(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = RelatedResourceOutput()

        # if self.metadata_merged.get('related_resources'):
        related_status = "fail"
        if self.testRelatedResourcesAvailable():
            related_status = "pass"
            self.testRelatedResourcesMachineReadable()
        self.result.metric_tests = self.metric_tests
        self.result.test_status = related_status
        self.result.maturity = self.maturity
        self.result.score = self.score
        self.result.output = self.output
