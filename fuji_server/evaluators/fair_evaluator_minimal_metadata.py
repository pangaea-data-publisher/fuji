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

        self.metric_test_map = {  # overall map
            "testMetadataCommonMethodsAvailable": ["FsF-F2-01M-1"],
            "testCoreDescriptiveMetadataAvailable": ["FsF-F2-01M-3", "FRSM-04-F2-2", "FRSM-04-F2-CESSDA-2"],
            "testCoreCitationMetadataAvailable": ["FsF-F2-01M-2"],
            "testMinimumMetadataAvailable": ["FRSM-04-F2-1", "FRSM-04-F2-CESSDA-1"],
            "testMetadataFormatMachineReadable": ["FRSM-04-F2-3"],
        }

    def testMetadataCommonMethodsAvailable(self):
        # implements FsF-F2-01M-1
        agnostic_test_name = "testMetadataCommonMethodsAvailable"
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.metric_tests.get(test_id).metric_test_score_config
            if len(self.metadata_found) >= 1:
                self.logger.info(
                    "FsF-F2-01M : Found some descriptive metadata elements -: " + str(self.metadata_found.keys())
                )
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                source_mechanisms = dict((y, x) for x, y in list(set(self.fuji.metadata_sources)))

                for source_mechanism in source_mechanisms:
                    if source_mechanism in [
                        MetadataOfferingMethods.META_TAGS,
                        MetadataOfferingMethods.JSON_IN_HTML,
                        MetadataOfferingMethods.RDFA,
                        MetadataOfferingMethods.MICRODATA,
                        # MetadataOfferingMethods.MICRODATA_RDFA,
                        # MetadataOfferingMethods.HTML_EMBEDDING,
                    ]:
                        self.setEvaluationCriteriumScore(f"{test_id}a", 0, "pass")
                    if source_mechanism == MetadataOfferingMethods.CONTENT_NEGOTIATION:
                        self.setEvaluationCriteriumScore(f"{test_id}b", 0, "pass")
                    if source_mechanism == MetadataOfferingMethods.TYPED_LINKS:
                        self.setEvaluationCriteriumScore(f"{test_id}c", 0, "pass")
                    if source_mechanism == MetadataOfferingMethods.SIGNPOSTING:
                        self.setEvaluationCriteriumScore(f"{test_id}d", 0, "pass")
                self.maturity = self.metric_tests.get(test_id).metric_test_maturity_config
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
        agnostic_test_name = "testCoreDescriptiveMetadataAvailable"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        test_requirements = None
        # TODO implement
        if test_id.startswith("FRSM"):
            self.logger.warning(
                f"{self.metric_identifier} : Test for descriptive metadata is not implemented for FRSM."
            )
        if test_defined:
            if self.metric_tests[test_id].metric_test_requirements:
                test_requirements = self.metric_tests[test_id].metric_test_requirements[0]
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
            test_score = self.getTestConfigScore(test_id)
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
        agnostic_test_name = "testCoreCitationMetadataAvailable"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        test_status = False
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            if set(self.partial_elements).issubset(self.metadata_found):
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier
                    + f" : Found required core citation metadata elements -: {self.partial_elements}",
                )
                self.maturity = self.metric_tests.get(test_id).metric_test_maturity_config
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned = self.score.earned + test_score
                test_status = True
        return test_status

    def testMinimumMetadataAvailable(self):
        """FAIR4Software specific... The software includes the software title and description. Considers different sources (e.g. README, Zenodo) depending on metric definition.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testMinimumMetadataAvailable"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for minimum metadata is not implemented.")
        return test_status

    def testMetadataFormatMachineReadable(self):
        """The metadata is contained in a format such as CodeMeta or ProjectObjectModel that enables full machine actionability.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testMetadataFormatMachineReadable"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for metadata format is not implemented.")
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
        if self.testMinimumMetadataAvailable():
            test_status = "pass"
            metadata_status = "some metadata"
        if self.testMetadataFormatMachineReadable():
            test_status = "pass"
            metadata_status = "machine-readable metadata"
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
