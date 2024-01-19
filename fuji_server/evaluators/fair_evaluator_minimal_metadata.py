# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_collector import MetadataOfferingMethods
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.models.core_metadata import CoreMetadata
from fuji_server.models.core_metadata_output import CoreMetadataOutput


class FAIREvaluatorCoreMetadata(FAIREvaluator):
    """
    A class to evaluate the metadata that includes core descriptive elements (creator, title, data identifier, publisher, publication date, summary, and
    keywords) to support data finding (F2-01M). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate metadata whether it specifies the core metadata, e.g., creator, title, publication date, etc.,
        through appropriate metadata fields.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FsF-F2-01M", "FRSM-04-F2"])
        self.metadata_found = {}
        # this list is following the recommendation of  DataCite see: Fenner et al 2019 and Starr & Gastl, 2011
        self.partial_elements = [
            "creator",
            "title",
            "object_identifier",
            "publication_date",
            "publisher",
            "object_type",
        ]
        self.required_metadata_properties = Mapper.REQUIRED_CORE_METADATA.value

    def testMetadataCommonMethodsAvailable(self):
        # implements FsF-F2-01M-1
        if self.isTestDefined("FsF-F2-01M-1"):
            test_score = self.metric_tests.get("FsF-F2-01M-1").metric_test_score_config
            if len(self.metadata_found) >= 1:
                self.logger.info(
                    "FsF-F2-01M : Found some descriptive metadata elements -: " + str(self.metadata_found.keys())
                )
                self.setEvaluationCriteriumScore("FsF-F2-01M-1", test_score, "pass")
                source_mechanisms = dict((y, x) for x, y in list(set(self.fuji.metadata_sources)))

                for source_mechanism in source_mechanisms:
                    if source_mechanism in [
                        MetadataOfferingMethods.MICRODATA_RDFA,
                        MetadataOfferingMethods.HTML_EMBEDDING,
                    ]:
                        self.setEvaluationCriteriumScore("FsF-F2-01M-1a", 0, "pass")
                    if source_mechanism == MetadataOfferingMethods.CONTENT_NEGOTIATION:
                        self.setEvaluationCriteriumScore("FsF-F2-01M-1b", 0, "pass")
                    if source_mechanism == MetadataOfferingMethods.TYPED_LINKS:
                        self.setEvaluationCriteriumScore("FsF-F2-01M-1c", 0, "pass")
                    if source_mechanism == MetadataOfferingMethods.SIGNPOSTING:
                        self.setEvaluationCriteriumScore("FsF-F2-01M-1d", 0, "pass")
                self.maturity = self.metric_tests.get("FsF-F2-01M-1").metric_test_maturity_config
                self.score.earned = test_score
                partial_missing = list(set(self.partial_elements) - set(self.metadata_found))
                if partial_missing:
                    self.logger.warning(
                        self.metric_identifier
                        + " : Not all required citation metadata elements exist, missing -: "
                        + str(partial_missing)
                    )

            return True
        else:
            return False

    def testCoreDescriptiveMetadataAvailable(self):
        test_status = False
        test_requirements = None
        if self.isTestDefined(self.metric_identifier + "-3"):
            if self.metric_tests[self.metric_identifier + "-3"].metric_test_requirements:
                test_requirements = self.metric_tests[self.metric_identifier + "-3"].metric_test_requirements[0]
            if test_requirements:
                test_required = []
                if test_requirements.get("required"):
                    if isinstance(test_requirements.get("required"), list):
                        test_required = test_requirements.get("required")
                    elif test_requirements.get("required").get("name"):
                        test_required = test_requirements.get("required").get("name")
                    if not isinstance(test_required, list):
                        test_required = [test_required]
                    self.logger.info(
                        "{} : Will exclusively consider community specific metadata properties which are specified in metrics -: {}".format(
                            self.metric_identifier, test_requirements.get("required")
                        )
                    )
                    self.required_metadata_properties = []
                    for rq_prop in test_required:
                        if rq_prop in Mapper.REFERENCE_METADATA_LIST.value:
                            self.required_metadata_properties.append(rq_prop)
            test_score = self.getTestConfigScore(self.metric_identifier + "-3")
            if set(self.metadata_found) & set(self.required_metadata_properties) == set(
                self.required_metadata_properties
            ):
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier
                    + f" : Found required core descriptive metadata elements -: {self.required_metadata_properties}",
                )
                self.maturity = self.metric_tests.get(self.metric_identifier + "-3").metric_test_maturity_config
                self.score.earned = self.total_score
                self.setEvaluationCriteriumScore(self.metric_identifier + "-3", test_score, "pass")
                test_status = True
            else:
                core_missing = list(set(self.required_metadata_properties) - set(self.metadata_found))
                self.logger.warning(
                    self.metric_identifier
                    + f" : Not all required core descriptive metadata elements exist, missing -: {core_missing!s}"
                )
        return test_status

    def testCoreCitationMetadataAvailable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            if set(self.partial_elements).issubset(self.metadata_found):
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier
                    + f" : Found required core citation metadata elements -: {self.partial_elements}",
                )
                self.maturity = self.metric_tests.get(self.metric_identifier + "-2").metric_test_maturity_config
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.score.earned = self.score.earned + test_score
                test_status = True
        return test_status

    def evaluate(self):
        if self.fuji.landing_url is None:
            self.logger.warning(
                self.metric_identifier
                + " : Metadata checks probably unreliable: landing page URL could not be determined"
            )
        self.result = CoreMetadata(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )

        test_status = "fail"
        metadata_status = "insufficient metadata"
        self.metadata_found = {
            k: v for k, v in self.fuji.metadata_merged.items() if k in Mapper.REFERENCE_METADATA_LIST.value
        }
        self.logger.info(
            self.metric_identifier + " : Testing if any metadata has been made available via common web standards"
        )
        if self.testMetadataCommonMethodsAvailable():
            test_status = "pass"
            metadata_status = "some metadata"
        if self.testCoreCitationMetadataAvailable():
            test_status = "pass"
            metadata_status = "partial metadata"
        if self.testCoreDescriptiveMetadataAvailable():
            test_status = "pass"
            metadata_status = "all metadata"
        output_sources = []
        for oi, os in list(set(self.fuji.metadata_sources)):
            output_sources.append((oi, os.acronym()))
        self.output = CoreMetadataOutput(core_metadata_status=metadata_status, core_metadata_source=output_sources)

        self.output.core_metadata_found = {
            k: v for k, v in self.metadata_found.items() if k in self.required_metadata_properties
        }

        self.result.test_status = test_status
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.output = self.output
