# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server import Persistence, PersistenceOutput
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.persistence_output_inner import PersistenceOutputInner


class FAIREvaluatorPersistentIdentifierData(FAIREvaluator):
    """
    A class to evaluate that the data is assigned a persistent identifier (F1-02D). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the data is specified based on a commonly accepted persistent identifier scheme or
        the identifier is web-accesible, i.e., it resolves to a landing page with metadata of the data object.
    """

    def __init__(self, fuji_instance):
        self.pids_which_resolve = {}
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-F1-02DD")

    def setPidsOutput(self):
        self.output.persistent_identifiers = []
        for pid_info in self.fuji.content_identifier.values():
            if pid_info.get("is_persistent"):
                output_inner = PersistenceOutputInner()
                output_inner.pid = pid_info.get("url")
                output_inner.pid_scheme = pid_info.get("scheme")
                if pid_info.get("resolved_url"):
                    output_inner.resolvable_status = True
                output_inner.resolved_url = pid_info.get("resolved_url")
                self.output.persistent_identifiers.append(output_inner)

    def testCompliesWithPIDScheme(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            for pid_info in self.fuji.content_identifier.values():
                # if pid_info.get('verified'):
                if pid_info.get("is_persistent"):
                    test_status = True
            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                self.score.earned = test_score
                self.maturity = self.metric_tests.get(self.metric_identifier + "-1").metric_test_maturity_config
                test_status = True
        return test_status

    def testIfLandingPageResolves(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            for pid_info in self.fuji.content_identifier.values():
                if pid_info.get("is_persistent"):
                    if pid_info.get("resolved_url"):
                        test_status = True
                        self.logger.info(
                            self.metric_identifier
                            + " : Found PID which could be verified (does resolve properly) -: "
                            + str(pid_info.get("url"))
                        )
                        break
                    else:
                        self.logger.info(
                            self.metric_identifier
                            + " : Found PID pointing to data which could not be verified (does not resolve properly) -: "
                            + str(pid_info.get("url"))
                        )
            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-2").metric_test_maturity_config
                self.score.earned = self.total_score  # idenfier should be based on a persistence scheme and resolvable
            self.logger.log(
                self.fuji.LOG_SUCCESS,
                self.metric_identifier
                + f" : Persistence identifier scheme for data identifier -: {self.fuji.pid_scheme}",
            )
        return test_status

    def evaluate(self):
        self.result = Persistence(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.result.test_status = "fail"
        self.setPidsOutput()
        if self.testCompliesWithPIDScheme():
            self.result.test_status = "pass"
        if self.testIfLandingPageResolves():
            self.result.test_status = "pass"

        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output
