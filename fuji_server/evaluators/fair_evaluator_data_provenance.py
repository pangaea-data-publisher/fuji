# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.models.data_provenance import DataProvenance
from fuji_server.models.data_provenance_output import DataProvenanceOutput
from fuji_server.models.data_provenance_output_inner import DataProvenanceOutputInner


class FAIREvaluatorDataProvenance(FAIREvaluator):
    """
    A class to evaluate metadata that includes provenance information about data creation or generation (R1.2-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate the provenance information such as properties representing data creation,
        e.g., creator, contributor, modification date, version, source, and relations that indicate
        data creation activities. Moreover, it evaluates whether provenance information is available in
        a machine-readabe version such PROV-O or PAV
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FsF-R1.2-01M", "FRSM-06-F2"])

        self.metric_test_map = {  # overall map
            "testProvenanceMetadataAvailable": ["FsF-R1.2-01M-1", "FRSM-06-F2-1"],
            "testProvenanceStandardsUsed": ["FsF-R1.2-01M-2"],
            "testCitationMetadata": ["FRSM-06-F2-2"],
            "testProportionalCredit": ["FRSM-06-F2-3"],
            "testFilesPresent": ["FRSM-06-F2-CESSDA-1"],
            "testORCIDInZenodoAndCitationFile": ["FRSM-06-F2-CESSDA-2"],
        }

    def testProvenanceMetadataAvailable(self):
        agnostic_test_name = "testProvenanceMetadataAvailable"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        # TODO implement
        if test_id.startswith("FRSM"):
            self.logger.warning(
                f"{self.metric_identifier} : Test for descriptive metadata is not implemented for FRSM."
            )
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            provenance_metadata_output = DataProvenanceOutputInner()
            provenance_metadata_output.provenance_metadata = []
            provenance_metadata_output.is_available = False
            self.logger.info(
                self.metric_identifier + " : Check if provenance information is available in descriptive metadata"
            )
            for md in self.fuji.metadata_merged:
                if md in Mapper.PROVENANCE_MAPPING.value:
                    provenance_metadata_output.is_available = True
                    provenance_metadata_output.provenance_metadata.append(
                        {
                            "prov_o_mapping": Mapper.PROVENANCE_MAPPING.value.get(md),
                            "metadata_element": md,
                            "metadata_value": self.fuji.metadata_merged.get(md),
                        }
                    )

            relateds = self.fuji.metadata_merged.get("related_resources")
            self.logger.info(
                self.metric_identifier
                + " : Check if provenance information is available in metadata about related resources"
            )
            if isinstance(relateds, list):
                for rm in relateds:
                    if rm.get("relation_type") in Mapper.PROVENANCE_MAPPING.value:
                        provenance_metadata_output.provenance_metadata.append(
                            {
                                "prov_o_mapping": Mapper.PROVENANCE_MAPPING.value.get(rm.get("relation_type")),
                                "metadata_element": "related." + str(rm.get("relation_type")),
                                "metadata_value": rm.get("related_resource"),
                            }
                        )
            else:
                self.logger.warning(
                    self.metric_identifier + " : No provenance information found in metadata about related resources"
                )

            if provenance_metadata_output.is_available:
                test_status = True
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier + " : Found data creation-related provenance information",
                )
                self.maturity = self.getTestConfigMaturity(test_id)
                self.score.earned = test_score
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
            self.output.provenance_metadata_included = provenance_metadata_output
        return test_status

    def testProvenanceStandardsUsed(self):
        agnostic_test_name = "testProvenanceStandardsUsed"
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        test_status = False
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            provenance_namespaces = [
                "http://www.w3.org/ns/prov",
                "http://www.w3.org/ns/prov#",
                "http://purl.org/pav/",
                "http://purl.org/pav",
            ]
            # structured provenance metadata available
            structured_metadata_output = DataProvenanceOutputInner()
            structured_metadata_output.provenance_metadata = []
            structured_metadata_output.is_available = False
            self.logger.info(
                self.metric_identifier + " : Check if provenance specific namespaces are listed in metadata"
            )

            used_provenance_namespace = list(set(provenance_namespaces).intersection(set(self.fuji.namespace_uri)))
            if used_provenance_namespace:
                test_status = True
                if self.fuji.metric_helper.get_metric_version() >= 0.8:
                    self.score.earned = test_score
                else:
                    self.score.earned += test_score
                structured_metadata_output.is_available = True
                for used_prov_ns in used_provenance_namespace:
                    structured_metadata_output.provenance_metadata.append({"namespace": used_prov_ns})
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.maturity = self.getTestConfigMaturity(test_id)
                self.logger.log(
                    self.fuji.LOG_SUCCESS, self.metric_identifier + " : Found use of dedicated provenance ontologies"
                )
            else:
                self.logger.warning(self.metric_identifier + " : Formal provenance metadata is unavailable")
            self.output.structured_provenance_available = structured_metadata_output
        return test_status

    def testCitationMetadata(self):
        """The software includes citation metadata that includes all contributors and their roles. This includes ORCIDs when contributors have them.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testCitationMetadata"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(f"{self.metric_identifier} : Test for citation metadata is not implemented.")
        return test_status

    def testProportionalCredit(self):
        """Does the citation metadata include the proportional credit attributed to each contributor?

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testProportionalCredit"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for proportional credit in citation metadata is not implemented."
            )
        return test_status

    def testFilesPresent(self):
        """A CITATION and/or CONTRIBUTORS files is present in the root of the repository.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testFilesPresent"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for presence of CITATION or CONTRIBUTORS file is not implemented."
            )
        return test_status

    def testORCIDInZenodoAndCitationFile(self):
        """Author details (including ORCIDs) are present in the corresponding Zenodo record. ORCIDs are present for authors in the CITATION.cff file.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testORCIDInZenodoAndCitationFile"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for author ORCIDs in CITATION file and Zenodo record is not implemented."
            )
        return test_status

    def evaluate(self):
        self.result = DataProvenance(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = DataProvenanceOutput()

        provenance_status = "fail"
        if self.testProvenanceMetadataAvailable():
            provenance_status = "pass"
        if self.testProvenanceStandardsUsed():
            provenance_status = "pass"
        if self.testCitationMetadata():
            provenance_status = "pass"
        if self.testProportionalCredit():
            provenance_status = "pass"
        if self.testFilesPresent():
            provenance_status = "pass"
        if self.testORCIDInZenodoAndCitationFile():
            provenance_status = "pass"

        self.result.test_status = provenance_status
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = self.output
        self.result.score = self.score
