# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.models.uniqueness_output import UniquenessOutput
from fuji_server.models.uniqueness_output_inner import UniquenessOutputInner


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
        if self.fuji.metric_helper.get_metric_version() >= 0.8:
            metric = "FsF-F1-01MD"
        else:
            metric = "FsF-F1-01D"
            # after 0.5 seperate metrics for metadata and data
        self.set_metric(metric)

    def testMetadataIdentifierCompliesWithIdutilsScheme(self):
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
                output_metadata_inner = UniquenessOutputInner()
                output_metadata_inner.guid = self.fuji.id
                output_metadata_inner.guid_scheme = found_id
                output_metadata_inner.target = "metadata"
                self.output.unique_identifiers.append(output_metadata_inner)
                #####

                # if idhelper.is_persistent:
                #    self.fuji.pid_scheme = found_id
                #    self.fuji.pid_url = idhelper.identifier_url
                self.logger.info(self.metric_identifier + f" : Finalized unique identifier scheme - {found_id}")
                test_status = True
        return test_status

    def testDataIdentifierCompliesWithUUIDorHASHorIdutilsScheme(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            self.logger.info(
                self.metric_identifier
                + " : Using idutils schemes to identify unique or persistent identifiers for data"
            )
            found_ids = []
            content_identifiers = self.fuji.content_identifier.values()
            if content_identifiers:
                for data_identifier in content_identifiers:
                    data_id_scheme = data_identifier.get("scheme")
                    self.logger.info(
                        self.metric_identifier + f" :Starting assessment on data identifier: {self.fuji.id}"
                    )
                    if data_id_scheme:
                        output_data_inner = UniquenessOutputInner()
                        output_data_inner.guid = data_identifier.get("url")
                        output_data_inner.guid_scheme = data_id_scheme
                        output_data_inner.target = "data"
                        self.output.unique_identifiers.append(output_data_inner)
                        found_ids.append(data_id_scheme)
            else:
                self.logger.warning(
                    self.metric_identifier
                    + " : Could NOT find any data identifier in metadata, therefore skipping uniqueness test"
                )
            if found_ids:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", self.total_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-2").metric_test_maturity_config

                self.output.guid = self.fuji.id
                self.score.earned += test_score
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + f" : Unique data identifier schemes found: - {list(set(found_ids))}",
                )
                self.output.guid_scheme = found_ids
                test_status = True
            else:
                self.logger.info(self.metric_identifier + " : NO unique data identifier schema found")

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

    # merged test for 0.6
    def testMetadataIdentifierCompliesWithUUIDorHASHorIdutilsScheme(self):
        test_status = False
        found_ids = []
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            self.logger.info(
                self.metric_identifier
                + " : Using IDUTILS schemes to identify unique or persistent identifiers for metadata"
            )
            idhelper = IdentifierHelper(self.fuji.id)
            found_ids.extend(idhelper.identifier_schemes)
            self.logger.info(self.metric_identifier + f" :Starting assessment on identifier: {self.fuji.id}")
            if len(found_ids) > 0:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + f" : Unique identifier schemes found {found_ids}",
                )
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-1").metric_test_maturity_config
                self.output.guid = self.fuji.id
                self.score.earned += test_score
                found_id = idhelper.preferred_schema
                self.fuji.id_scheme = idhelper.identifier_schemes[0]
                if idhelper.is_persistent:
                    self.fuji.pid_scheme = found_id
                    self.fuji.pid_url = idhelper.identifier_url
                self.logger.info(self.metric_identifier + f" : Finalized unique identifier scheme - {found_id}")
                self.output.guid_scheme = found_id

                output_metadata_inner = UniquenessOutputInner()
                output_metadata_inner.guid = self.fuji.id
                output_metadata_inner.guid_scheme = found_id
                output_metadata_inner.target = "metadata"
                self.output.unique_identifiers.append(output_metadata_inner)
                test_status = True
        return test_status

    def evaluate(self):
        # ======= CHECK IDENTIFIER UNIQUENESS =======
        if self.metric_identifier in self.metrics:
            self.result = Uniqueness(
                id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
            )
            self.output = UniquenessOutput()
            self.output.unique_identifiers = []
            self.result.test_status = "fail"
            self.score.earned = 0
            print("METRIC VERS : ", type(self.fuji.metric_helper.get_metric_version()))
            if self.fuji.metric_helper.get_metric_version() <= 0.5:
                if self.testMetadataIdentifierCompliesWithUUIDorHASH():
                    self.result.test_status = "pass"
                if self.testMetadataIdentifierCompliesWithIdutilsScheme():
                    self.result.test_status = "pass"
            else:
                if self.testMetadataIdentifierCompliesWithUUIDorHASHorIdutilsScheme():
                    self.result.test_status = "pass"
                if self.testDataIdentifierCompliesWithUUIDorHASHorIdutilsScheme():
                    self.result.test_status = "pass"
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
