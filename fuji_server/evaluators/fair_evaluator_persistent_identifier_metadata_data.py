# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server import Persistence, PersistenceOutput
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.models.persistence_output_inner import PersistenceOutputInner


class FAIREvaluatorPersistentIdentifierMetadataData(FAIREvaluator):
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
        if self.fuji.metric_helper.get_metric_version() > 0.5:
            metric = "FsF-F1-02MD"
        else:
            metric = "FsF-F1-02D"
        self.set_metric(metric)

    def setPidsOutput(self):
        self.output.persistent_identifiers = []
        for pid, pid_info in self.fuji.pid_collector.items():
            if pid_info.get("is_persistent"):
                output_metadata_inner = PersistenceOutputInner()
                output_metadata_inner.pid = pid_info.get("pid")
                output_metadata_inner.pid_scheme = pid_info.get("scheme")
                if pid_info.get("resolved_url"):
                    output_metadata_inner.resolvable_status = True
                output_metadata_inner.resolved_url = pid_info.get("resolved_url")
                output_metadata_inner.target = "metadata"
                self.output.persistent_identifiers.append(output_metadata_inner)
        for pid_info in self.fuji.content_identifier.values():
            if pid_info.get("is_persistent"):
                output_data_inner = PersistenceOutputInner()
                output_data_inner.pid = pid_info.get("pid")
                output_data_inner.pid_scheme = pid_info.get("scheme")
                if pid_info.get("resolved_url"):
                    output_data_inner.resolvable_status = True
                output_data_inner.resolved_url = pid_info.get("resolved_url")
                output_data_inner.target = "data"
                self.output.persistent_identifiers.append(output_data_inner)

    def testMetadataIdentifierCompliesWithPIDScheme(self, pid_dict):
        test_status = False
        remaining_pid_dict = {}
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            for pid, pid_info in pid_dict.items():
                if pid_info.get("is_persistent"):
                    remaining_pid_dict[pid] = pid_info
                    # for older versions of metric (<0.6)which do not test this separately
                    if not self.isTestDefined(self.metric_identifier + "-3") and not pid_info.get("verified"):
                        remaining_pid_dict.pop(pid, None)
                        self.logger.warning(
                            self.metric_identifier
                            + " : PID syntax is OK but the PID seems to resolve to a different entity, will not use this PID for content negotiation"
                        )
            if remaining_pid_dict:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                self.score.earned = test_score
                self.maturity = self.metric_tests.get(self.metric_identifier + "-1").metric_test_maturity_config
                test_status = True
            else:
                self.logger.info(
                    self.metric_identifier
                    + " : Could not find any persistent identifier for metadata which complies with a known PID syntax"
                )
        return test_status, remaining_pid_dict

    def testIfMetadataPersistentIdentifierIsRegistered(self, pid_dict):
        test_status = False
        remaining_pid_dict = {}
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            for pid, pid_info in pid_dict.items():
                if pid_info.get("is_persistent"):
                    if pid_info.get("status_list"):
                        if isinstance(pid_info.get("status_list"), list):
                            if str(pid_info.get("status_list")[0]).startswith("3"):
                                test_status = True
                                self.logger.info(
                                    self.metric_identifier
                                    + " : Found PID for metadata or landing page which is registered by a PID system (is found and redirected by PID system) -: "
                                    + str(pid_info.get("url"))
                                )
                                break
                            else:
                                self.logger.warning(
                                    self.metric_identifier
                                    + " : Found PID pointing to metadata or landing page which is NOT registered (does not resolve properly) -: "
                                    + str(pid_info.get("url"))
                                )
            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-2").metric_test_maturity_config
                if test_score:
                    if self.score.earned + test_score <= self.score.total:
                        self.score.earned += test_score
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + f" : Found persistence identifier scheme -: {self.fuji.pid_scheme}",
                )
            else:
                self.logger.warning(
                    self.metric_identifier
                    + " : Could not find any persistent identifier for metadata which is registered"
                )
        return test_status, remaining_pid_dict

    def testIfMetadataIdentifierPersistentIdentifierResolvestoDomain(self, pid_dict):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-3"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-3")
            for pid, pid_info in pid_dict.items():
                if pid_info.get("verified"):
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        self.metric_identifier
                        + " : Found PID could be verified, it resolves back to the domain of landing page-: "
                        + str(pid),
                    )
                    test_status = True
                    self.setEvaluationCriteriumScore(self.metric_identifier + "-3", test_score, "pass")
                    self.maturity = self.metric_tests.get(self.metric_identifier + "-3").metric_test_maturity_config
                    if test_score:
                        if self.score.earned + test_score <= self.score.total:
                            self.score.earned += test_score
                else:
                    self.logger.warning(
                        self.metric_identifier
                        + " : Found PID could NOT be verified since it resolves to a different domain than those of the landing page-: "
                        + str(pid)
                    )
        return test_status

    def testIfDataIdentifierIsRegistered(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-5"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-5")
            for pid_info in self.fuji.content_identifier.values():
                if pid_info.get("is_persistent"):
                    if pid_info.get("status_list"):
                        if isinstance(pid_info.get("status_list"), list):
                            if str(pid_info.get("status_list")[0]).startswith("3"):
                                test_status = True
                                self.logger.info(
                                    self.metric_identifier
                                    + " : Found PID for data which is registered by a PID system (is found and redirected by PID system) -: "
                                    + str(pid_info.get("url"))
                                )
                                break
                            else:
                                self.logger.warning(
                                    self.metric_identifier
                                    + " : Found PID pointing to data which is NOT registered (does not resolve properly) -: "
                                    + str(pid_info.get("url"))
                                )

            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-5", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-5").metric_test_maturity_config
                if test_score:
                    if self.score.earned + test_score <= self.score.total:
                        self.score.earned += test_score
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier
                    + f" : Persistence identifier scheme for data identifier -: {self.fuji.pid_scheme}",
                )
            else:
                self.logger.info(
                    self.metric_identifier + " : Could not find any persistent identifier for data which is registered"
                )
        return test_status

    def testDataIdentifierCompliesWithPIDScheme(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-4"):  # 1-3 already used in metadata PID tests
            test_score = self.getTestConfigScore(self.metric_identifier + "-4")
            for pid_info in self.fuji.content_identifier.values():
                # if pid_info.get('verified'):
                if pid_info.get("is_persistent"):
                    test_status = True
            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-4", test_score, "pass")
                if test_score:
                    if self.score.earned + test_score <= self.score.total:
                        self.score.earned += test_score
                self.maturity = self.metric_tests.get(self.metric_identifier + "-4").metric_test_maturity_config
                test_status = True
            else:
                self.logger.info(
                    self.metric_identifier
                    + " : Could not find any persistent identifier for data which complies with a known PID syntax"
                )
        return test_status

    def evaluate(self):
        self.result = Persistence(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.logger.info(
            self.metric_identifier
            + " : PID schemes-based assessment supported by the assessment service - {}".format(
                IdentifierHelper.VALID_PIDS.keys()
            )
        )

        self.result.test_status = "fail"
        self.setPidsOutput()
        input_pid_dict = self.fuji.pid_collector
        rest_pid_dict = {}
        metadata_test_status, rest_pid_dict = self.testMetadataIdentifierCompliesWithPIDScheme(input_pid_dict)
        if metadata_test_status:
            self.result.test_status = "pass"
        metadata_test_status, rest_pid_dict = self.testIfMetadataPersistentIdentifierIsRegistered(rest_pid_dict)
        if metadata_test_status:
            self.result.test_status = "pass"
        if self.testIfMetadataIdentifierPersistentIdentifierResolvestoDomain(rest_pid_dict):
            self.result.test_status = "pass"

        if self.fuji.metric_helper.get_metric_version() > 0.5:
            self.result.test_status = "fail"
            data_test_status = self.testDataIdentifierCompliesWithPIDScheme()
            if data_test_status and metadata_test_status:
                self.result.test_status = "pass"
            if self.testIfDataIdentifierIsRegistered() and metadata_test_status:
                self.result.test_status = "pass"
        """else:
            self.score.earned = 0
            self.logger.warning(self.metric_identifier + ' : Could not identify a valid peristent identifier based on scheme and resolution')"""

        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output
