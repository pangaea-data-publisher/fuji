# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server import OutputSearchMechanisms
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.catalogue_helper import MetaDataCatalogue
from fuji_server.helper.catalogue_helper_datacite import MetaDataCatalogueDataCite
from fuji_server.helper.catalogue_helper_google_datasearch import MetaDataCatalogueGoogleDataSearch
from fuji_server.helper.catalogue_helper_mendeley_data import MetaDataCatalogueMendeleyData
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.helper.metadata_collector import MetadataSources
from fuji_server.models.searchable import Searchable
from fuji_server.models.searchable_output import SearchableOutput


class FAIREvaluatorSearchable(FAIREvaluator):
    """
    A class to evaluate whether the metadata is offered to be retrievable by the machine (F4-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the metadata is registered in major research data registries such as DataCite or
        the metadata is given in a way major search engines can ingest it, e.g., JSON-LD, Dublin Core, RDFa.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-F4-01M")
        self.search_mechanisms = []
        self.search_engines_support_offering = ["json_in_html", "meta_tag", "microdata", "rdfa"]
        self.search_engines_support_standards = [
            "schemaorg",
            "dublin-core",
            "dcat-data-catalog-vocabulary",
        ]  # from f-uji.net/vocab/metadata/standards
        self.search_engines_support = [
            MetadataSources.SCHEMAORG_NEGOTIATED.name,
            MetadataSources.SCHEMAORG_EMBEDDED.name,
            MetadataSources.DUBLINCORE_EMBEDDED.name,
            MetadataSources.RDFA_EMBEDDED.name,
        ]
        self.sources_registry = [
            MetaDataCatalogue.Sources.DATACITE,
            MetaDataCatalogue.Sources.MENDELEY_DATA,
            MetaDataCatalogue.Sources.GOOGLE_DATASET,
        ]

    def testMetadataExchangeStandardsAvailable(self):
        # test for oai, csw, sparql
        test_status = False
        standards_supported = []

        if self.isTestDefined(self.metric_identifier + "-3"):
            if self.fuji.use_datacite:
                self.logger.info(
                    self.metric_identifier
                    + " : Trying to identify a metadata exchange standard given as input or via re3data entry"
                )
                test_score = self.getTestConfigScore(self.metric_identifier + "-3")
                if not self.fuji.oaipmh_endpoint:
                    self.logger.info(
                        "{} : Inferring metadata service endpoint (OAI) information through re3data/datacite services".format(
                            self.metric_identifier
                        )
                    )
                    self.fuji.oaipmh_endpoint = self.fuji.repo_helper.getRe3MetadataAPIs().get("OAI-PMH")
                if self.fuji.oaipmh_endpoint:
                    standards_supported.append("OAI-PMH")
                if self.fuji.csw_endpoint:
                    standards_supported.append("OGC-CSW")
                if not self.fuji.sparql_endpoint:
                    self.logger.info(
                        "{} : Inferring metadata service endpoint (SPARQL) information through re3data/datacite services".format(
                            self.metric_identifier
                        )
                    )
                    self.fuji.sparql_endpoint = self.fuji.repo_helper.getRe3MetadataAPIs().get("SPARQL")
                if self.fuji.sparql_endpoint:
                    standards_supported.append("SPARQL")
                if standards_supported:
                    self.setEvaluationCriteriumScore(self.metric_identifier + "-3", test_score, "pass")
                    self.set_maturity(self.getTestConfigMaturity(self.metric_identifier + "-3"))
                    self.score.earned += test_score
                    # standards_supported.append(self.fuji.self.metadata_service_type)
                    self.search_mechanisms.append(
                        OutputSearchMechanisms(mechanism="exchange standard", mechanism_info=standards_supported)
                    )
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        self.metric_identifier
                        + " : Metadata found - metadata exchange standard -: "
                        + str(standards_supported),
                    )
                else:
                    self.logger.warning(self.metric_identifier + " : No metadata exchange standard found")
            else:
                self.logger.warning(
                    self.metric_identifier
                    + " : Datacite support disabled, therefore skipping re3data metadata exchange standard check"
                )

        return test_status

    def filter_requirements(self, testid):
        test_requirements = []
        if self.metric_tests[self.metric_identifier + str(testid)].metric_test_requirements:
            test_requirements = self.metric_tests[self.metric_identifier + str(testid)].metric_test_requirements
        if test_requirements:
            for test_requirement in test_requirements:
                if test_requirement.get("required"):
                    test_required = []
                    if isinstance(test_requirement.get("required"), list):
                        test_required = test_requirement.get("required")
                    elif test_requirement.get("required").get("name"):
                        test_required = test_requirement.get("required").get("name")
                    if not isinstance(test_required, list):
                        test_required = [test_required]

                if "metadata/standard" in test_requirement.get("target"):
                    if test_required:
                        self.logger.info(
                            "{0} : Will exclusively consider community specific metadata standards for {0}{1} which are specified in metrics -: {2}".format(
                                self.metric_identifier, str(testid), test_required
                            )
                        )
                        self.search_engines_support_standards = test_required
                if "metadata/offering_method" in test_requirement.get("target"):
                    if test_required:
                        self.logger.info(
                            "{0} : Will exclusively consider community specific metadata offering methods for {0}{1} which are specified in metrics -: {2}".format(
                                self.metric_identifier, str(testid), test_required
                            )
                        )
                        self.search_engines_support_offering = test_required

    def testSearchEngineCompatibleMetadataAvailable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            self.filter_requirements("-1")
            search_engine_support_match = []
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            # NEW Way
            for found_metadata in self.fuji.metadata_unmerged:
                if found_metadata.get("metadata"):
                    if found_metadata.get("metadata") != {"object_type": "Other"}:
                        if found_metadata.get("offering_method") in self.search_engines_support_offering:
                            standard_found = found_metadata.get("metadata_standard")
                            if standard_found in self.search_engines_support_standards:
                                search_engine_support_match.append(
                                    standard_found + " via: " + found_metadata.get("offering_method")
                                )
                    else:
                        self.logger.info(
                            self.metric_identifier
                            + "Found RDFa like metadata which however is empty thus useless for search engines"
                        )
            search_engine_support_match = list(set(search_engine_support_match))
            # Check search mechanisms based on sources of metadata extracted.
            if search_engine_support_match:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                self.set_maturity(self.getTestConfigMaturity(self.metric_identifier + "-1"))
                self.score.earned += test_score
                test_status = True
                self.search_mechanisms.append(
                    OutputSearchMechanisms(mechanism="structured data", mechanism_info=search_engine_support_match)
                )
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier
                    + " :  Metadata is offered in a way major search engines can ingest it -: "
                    + str(search_engine_support_match),
                )
            else:
                self.logger.warning(
                    self.metric_identifier
                    + f" : Metadata is NOT found through -: {self.search_engines_support_offering}"
                )
        return test_status

    def testListedinSearchEngines(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            # check if record is listed in major catalogs -> searchable
            # DataCite registry, Google Dataset search, Mendeley data etc..
            # Using the DataCite API in case content negotiation does not work
            registries_supported = []
            if self.fuji.pid_url or self.fuji.landing_url:
                # DataCite only for DOIs
                pidhelper = IdentifierHelper(self.fuji.pid_url)
                if self.fuji.pid_scheme:
                    if "doi" in self.fuji.pid_scheme:
                        datacite_registry_helper = MetaDataCatalogueDataCite(self.fuji.logger)
                        datacite_registry_helper.query(pidhelper.normalized_id)
                        if datacite_registry_helper.islisted:
                            registries_supported.append(datacite_registry_helper.source)
                if not registries_supported:
                    google_registry_helper = MetaDataCatalogueGoogleDataSearch(
                        self.fuji.logger, self.fuji.metadata_merged.get("object_type")
                    )
                    google_registry_helper.query([pidhelper.normalized_id, self.fuji.landing_url])
                    if google_registry_helper.islisted:
                        registries_supported.append(google_registry_helper.source)
                else:
                    self.logger.info(
                        self.metric_identifier
                        + " : Dataset already found in registry therefore skipping Google Dataset Search Cache query"
                    )

                if not registries_supported:
                    mendeley_registry_helper = MetaDataCatalogueMendeleyData(self.fuji.logger)
                    mendeley_registry_helper.query([pidhelper.normalized_id, self.fuji.landing_url])
                    if mendeley_registry_helper.islisted:
                        registries_supported.append(mendeley_registry_helper.source)
                else:
                    self.logger.info(
                        self.metric_identifier
                        + " : Dataset already found in registry therefore skipping Mendeley Data query"
                    )
            else:
                self.logger.warning(
                    self.metric_identifier
                    + " : No resolvable PID or responding landing page found, therefore skipping data catalogue coverage tests"
                )
            if registries_supported:
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.set_maturity(self.getTestConfigMaturity(self.metric_identifier + "-2"))
                self.score.earned += test_score
                self.search_mechanisms.append(
                    OutputSearchMechanisms(mechanism="metadata registry", mechanism_info=registries_supported)
                )
                self.logger.log(
                    self.fuji.LOG_SUCCESS, self.metric_identifier + " : Metadata found through - metadata registry"
                )
            else:
                self.logger.warning(
                    self.metric_identifier
                    + " : Metadata is NOT found through registries considered by the assessment service  -: {}".format(
                        [s.name for s in self.sources_registry]
                    )
                )
        return test_status

    def evaluate(self):
        self.result = Searchable(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        self.output = SearchableOutput()

        searchable_status = "fail"
        if self.testSearchEngineCompatibleMetadataAvailable():
            searchable_status = "pass"
        if self.testListedinSearchEngines():
            searchable_status = "pass"
        if self.testMetadataExchangeStandardsAvailable():
            searchable_status = "pass"
        else:
            self.logger.warning("NO search mechanism supported")
        self.result.test_status = searchable_status
        self.result.score = self.score
        self.output.search_mechanisms = self.search_mechanisms
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = self.output
