# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.retrievable import Retrievable
from fuji_server.models.retrievable_output import RetrievableOutput
from fuji_server.models.retrievable_output_inner import RetrievableOutputInner


class FAIREvaluatorMetadataDataRetrievable(FAIREvaluator):
    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-A1-02MD")

    def testMetadataRetrievable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            # print(self.fuji.landing_url, self.fuji.origin_url, self.fuji.pid_url)
            visited_urls = []
            for meta in self.fuji.metadata_unmerged:
                # here retrievable means: page was resolved and some metadata is there
                if meta.get("url") and meta.get("url") not in visited_urls:
                    visited_urls.append(meta.get("url"))
                    if isinstance(meta.get("metadata"), dict):
                        retrievable_object = RetrievableOutputInner()
                        retrievable_object.method = meta.get("offering_method")
                        retrievable_object.format = meta.get("schema")
                        retrievable_object.resolved_url = meta.get("url")
                        retrievable_object.target = "metadata"
                        self.output.retrievable_objects.append(retrievable_object)
                        test_status = True
                        if meta.get("offering_method") == "signposting":
                            self.logger.info(
                                self.metric_identifier
                                + " : Identifier led to signposting link to metadata -: "
                                + str(meta.get("url"))
                            )
                        if len(meta.get("metadata").keys()) == 0:
                            self.logger.info(
                                self.metric_identifier
                                + " : Found metadata based on namespace but obviously could not parse it -:"
                                + str(meta.get("schema"))
                            )

            if test_status:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + " : Found retrievable metadata using the given identifier",
                )
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                # self.output.guid = self.fuji.id
                self.maturity = self.metric_tests.get(self.metric_identifier + "-1").metric_test_maturity_config
                self.score.earned += test_score
            else:
                self.logger.warning(
                    self.metric_identifier + " : Found NO retrievable metadata using the given identifier"
                )
        return test_status

    def testDataRetrievable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            # print(self.fuji.landing_url, self.fuji.origin_url, self.fuji.pid_url)
            # for meta in self.fuji.metadata_unmerged:
            for meta in self.fuji.content_identifier.values():
                # print('DATA INFO :  ',meta)
                # here retrievable means: page was resolved and some metadata is there
                if meta.get("scheme") and meta.get("status_code"):
                    if str(meta.get("status_code")).startswith("20"):
                        retrievable_object = RetrievableOutputInner()
                        retrievable_object.method = meta.get("scheme")
                        retrievable_object.format = meta.get("clained_type")
                        retrievable_object.resolved_url = meta.get("url")
                        retrievable_object.target = "data"
                        self.output.retrievable_objects.append(retrievable_object)
                        test_status = True
                    else:
                        self.logger.info(
                            self.metric_identifier
                            + " : Data link inaccessible, status code: -: "
                            + str((meta.get("url"), meta.get("status_code")))
                        )
            if test_status:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + " : Found retrievable data using the given identifier",
                )
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                # self.output.guid = self.fuji.id
                self.maturity = self.metric_tests.get(self.metric_identifier + "-2").metric_test_maturity_config
                self.score.earned += test_score
            else:
                self.logger.warning(self.metric_identifier + " : Found NO retrievable data using the given identifier")
        return test_status

    def evaluate(self):
        self.score.earned = 0
        self.result = Retrievable(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = RetrievableOutput()
        self.output.retrievable_objects = []
        self.result.test_status = "fail"
        if self.testMetadataRetrievable():
            self.result.test_status = "pass"
        if self.testDataRetrievable():
            self.result.test_status = "pass"

        self.result.score = self.score
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output
        self.result.maturity = self.maturity
