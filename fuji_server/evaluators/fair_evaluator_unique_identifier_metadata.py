# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.models.uniqueness_output import UniquenessOutput


class FAIREvaluatorUniqueIdentifierMetadata(FAIREvaluator):
    """
    A class to evaluate the globally unique identifier of the data (F1-01D). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the data is assigned to a unique identifier (UUID/HASH) that folows a proper syntax or
        identifier is resolvable and follows a defined unique identifier syntax (URL, IRI).
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        if self.fuji.metric_helper.get_metric_version() != "0.5":
            metric = "FsF-F1-01M"
        else:
            metric = "FsF-F1-01D"
            # after 0.5 seperate metrics for metadata and data
        self.set_metric(metric)

    def testMetadataIdentifierCompliesWithIdutilsScheme(self, validschemes=[]):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            self.logger.info(
                self.metric_identifier
                + " : Using idutils schemes to identify unique or persistent identifiers for metadata"
            )
            idhelper = IdentifierHelper(self.fuji.id)
            found_ids = idhelper.identifier_schemes
            self.logger.info(self.metric_identifier + f" :Starting assessment on identifier: {self.fuji.id}")
            if len(found_ids) > 0:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + f" : Unique identifier schemes found {found_ids}",
                )
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", self.total_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-1").metric_test_maturity_config
                self.output.guid = self.fuji.id
                self.score.earned = self.total_score
                found_id = idhelper.preferred_schema
                self.fuji.id_scheme = idhelper.identifier_schemes[0]
                if idhelper.is_persistent:
                    self.fuji.pid_scheme = found_id
                    self.fuji.pid_url = idhelper.identifier_url
                self.logger.info(self.metric_identifier + f" : Finalized unique identifier scheme - {found_id}")
                self.output.guid_scheme = found_id
                test_status = True
        return test_status

    def testMetadataIdentifierCompliesWithUUIDorHASH(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            idhelper = IdentifierHelper(self.fuji.id)
            if idhelper.preferred_schema == "uuid":
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + " : Unique identifier (UUID) scheme for metadata identifier found",
                )
                self.output.guid_scheme = "uuid"
                test_status = True
            elif idhelper.preferred_schema == "hash":
                self.output.guid_scheme = "hash"
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + " : Unique identifier (SHA,MD5) scheme for metadata identifier found",
                )
                test_status = True
            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.output.guid = self.fuji.id
                self.maturity = self.maturity = self.metric_tests.get(
                    self.metric_identifier + "-2"
                ).metric_test_maturity_config
                self.score.earned = test_score
        return test_status

    def evaluate(self):
        # ======= CHECK IDENTIFIER UNIQUENESS =======
        if self.metric_identifier in self.metrics:
            self.result = Uniqueness(
                id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
            )
            self.output = UniquenessOutput()
            self.result.test_status = "fail"
            if self.testMetadataIdentifierCompliesWithUUIDorHASH():
                self.result.test_status = "pass"
            if self.testMetadataIdentifierCompliesWithIdutilsScheme():
                self.result.test_status = "pass"
            else:
                self.result.test_status = "fail"
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the identifier scheme!.")
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
