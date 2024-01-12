# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.models.uniqueness_output import UniquenessOutput


class FAIREvaluatorUniqueIdentifierData(FAIREvaluator):
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
        metric = "FsF-F1-01DD"
        self.set_metric(metric)

    def testDataIdentifierCompliesWithIdutilsScheme(self, validschemes=[]):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            self.logger.info(
                self.metric_identifier
                + " : Using idutils schemes to identify unique or persistent identifiers for data"
            )
            # contents = self.fuji.metadata_merged.get('object_content_identifier')
            contents = self.fuji.content_identifier
            for content in contents.values():
                if content.get("url"):
                    idhelper = IdentifierHelper(content.get("url"))
                    found_ids = idhelper.identifier_schemes
                    if len(found_ids) > 0:
                        self.logger.log(
                            self.fuji.LOG_SUCCESS,
                            self.metric_identifier
                            + " : Unique identifier schemes found for data URI -: {} as {}".format(
                                str(content.get("url")), found_ids
                            ),
                        )
                        self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                        self.maturity = self.metric_tests.get(self.metric_identifier + "-1").metric_test_maturity_config
                        self.output.guid = content.get("url")
                        self.output.guid_scheme = idhelper.preferred_schema
                        self.score.earned += test_score
                        test_status = True
                        break
        return test_status

    def testDataIdentifierCompliesWithUUIDorHASH(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            contents = self.fuji.content_identifier
            for content in contents.values():
                if content.get("url") and content.get("schema"):
                    if content.get("schema") == "uuid":
                        self.logger.log(
                            self.fuji.LOG_SUCCESS,
                            self.metric_identifier + " : Unique identifier (UUID) scheme for data identifier found",
                        )
                        self.output.guid_scheme = "uuid"
                        test_status = True
                        break
                    elif content.get("schema") == "hash":
                        self.output.guid_scheme = "hash"
                        self.logger.log(
                            self.fuji.LOG_SUCCESS,
                            self.metric_identifier + " : Unique identifier (SHA,MD5) scheme for data identifier found",
                        )
                        test_status = True
                        break
            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.output.guid = content.get("url")
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
            if self.testDataIdentifierCompliesWithIdutilsScheme():
                self.result.test_status = "pass"
            if self.testDataIdentifierCompliesWithUUIDorHASH():
                self.result.test_status = "pass"
            else:
                self.result.test_status = "fail"
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the identifier scheme!.")
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
