# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_collector import MetadataSources
from fuji_server.helper.metadata_provider_sparql import SPARQLMetadataProvider
from fuji_server.models.formal_metadata import FormalMetadata
from fuji_server.models.formal_metadata_output_inner import FormalMetadataOutputInner


class FAIREvaluatorFormalMetadata(FAIREvaluator):
    """
    A class to evaluate that the metadata is represented using a formal knowledge representation language (I1-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the metadata is parsable and has a structured data embedded in the landing page or
        formal metadata, e.g., RDF, JSON-LD, is accessible.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-I1-01M")
        self.outputs = []

    def testEmbeddedStructuredMetadataAvailable(self):
        # 1. light-weight check (structured_data), expected keys from extruct ['json-ld','rdfa']
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            self.logger.info(
                f"{self.metric_identifier} : Check of structured data (RDF serialization) embedded in the data page"
            )
            if MetadataSources.SCHEMAORG_EMBEDDED.name in dict(self.fuji.metadata_sources):
                self.outputs.append(
                    FormalMetadataOutputInner(
                        serialization_format="JSON-LD", source="structured_data", is_metadata_found=True
                    )
                )
                self.logger.info(
                    "{} : JSON-LD (schema.org) serialization found in the data page - {}".format(
                        self.metric_identifier, "JSON-LD"
                    )
                )
            if MetadataSources.RDFA_EMBEDDED.name in dict(self.fuji.metadata_sources):
                self.outputs.append(
                    FormalMetadataOutputInner(
                        serialization_format="RDFa", source="structured_data", is_metadata_found=True
                    )
                )
                self.logger.info(
                    "{} : RDFa serialization found in the data page - {}".format(self.metric_identifier, "RDFa")
                )

            if len(self.outputs) == 0:
                self.logger.info(
                    f"{self.metric_identifier} : NO structured data (RDF serialization) embedded in the data page"
                )
            else:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    f"{self.metric_identifier} : Found structured data (RDF serialization) in the data page",
                )
                self.score.earned += test_score
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + "-1")
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")

        return test_status

    def testExternalStructuredMetadataAvailable(self):
        # 2. hard check (typed-link, content negotiate, sparql endpoint)
        # 2a. in the object page, you may find a <link rel="alternate" type="application/rdf+xml" … />
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            self.logger.info(f"{self.metric_identifier} : Check if RDF-based typed link included")
            if MetadataSources.RDF_TYPED_LINKS.name in dict(
                self.fuji.metadata_sources
            ) or MetadataSources.RDF_SIGNPOSTING_LINKS.name in dict(self.fuji.metadata_sources):
                self.logger.info(
                    "{} : RDF graph retrieved via typed link, content type - {}".format(self.metric_identifier, "RDF")
                )
                self.outputs.append(
                    FormalMetadataOutputInner(serialization_format="RDF", source="typed_link", is_metadata_found=True)
                )
                test_status = True
            else:
                self.logger.info(f"{self.metric_identifier} : NO RDF-based typed link found")

            # 2b.content negotiate
            self.logger.info(f"{self.metric_identifier} : Check if RDF metadata available through content negotiation")

            if MetadataSources.SCHEMAORG_NEGOTIATED.name in dict(self.fuji.metadata_sources):
                self.logger.info(
                    "{} : JSON-LD graph retrieved through content negotiation, content type - {}".format(
                        self.metric_identifier, "JSON-LD"
                    )
                )
                self.outputs.append(
                    FormalMetadataOutputInner(
                        serialization_format="JSON-LD", source="content_negotiate", is_metadata_found=True
                    )
                )
                test_status = True

            if MetadataSources.RDF_NEGOTIATED.name in dict(self.fuji.metadata_sources):
                self.logger.info(
                    "{} : RDF graph retrieved through content negotiation, content type - {}".format(
                        self.metric_identifier, "RDF"
                    )
                )
                self.outputs.append(
                    FormalMetadataOutputInner(
                        serialization_format="RDF", source="content_negotiate", is_metadata_found=True
                    )
                )
                test_status = True
            if test_status:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    f"{self.metric_identifier} : Found RDF content through content negotiation or typed links",
                )
            else:
                self.logger.info(f"{self.metric_identifier} : NO RDF metadata available through content negotiation")
                # 2c. try to retrieve via sparql endpoint (if available)
                # self.logger.info('{0} : Check if SPARQL endpoint is available'.format(formal_meta_identifier))
                # self.sparql_endpoint = 'http://data.archaeologydataservice.ac.uk/sparql/repositories/archives' #test endpoint
                # self.sparql_endpoint = 'http://data.archaeologydataservice.ac.uk/query/' #test web sparql form
                # self.pid_url = 'http://data.archaeologydataservice.ac.uk/10.5284/1000011' #test uri
                # self.sparql_endpoint = 'https://meta.icos-cp.eu/sparqlclient/' #test endpoint
                # self.pid_url = 'https://meta.icos-cp.eu/objects/9ri1elaogsTv9LQFLNTfDNXm' #test uri
                if self.fuji.sparql_endpoint:
                    self.logger.info(f"{self.metric_identifier} : SPARQL endpoint found -: {self.fuji.sparql_endpoint}")
                    sparql_provider = SPARQLMetadataProvider(
                        endpoint=self.fuji.sparql_endpoint, logger=self.logger, metric_id=self.metric_identifier
                    )
                    if self.fuji.pid_url is None:
                        url_to_sparql = self.fuji.landing_url
                    else:
                        url_to_sparql = self.fuji.pid_url
                    query = "DESCRIBE <" + str(url_to_sparql) + ">"
                    # query = "CONSTRUCT {{?dataURI ?property ?value}} where {{ VALUES ?dataURI {{ <"+str(url_to_sparql)+"> }} ?dataURI ?property ?value }}"
                    self.logger.info(f"{self.metric_identifier} : Executing SPARQL -: {query}")
                    rdfgraph, contenttype = sparql_provider.getMetadata(query)
                    if rdfgraph:
                        self.outputs.append(
                            FormalMetadataOutputInner(
                                serialization_format=contenttype, source="sparql_endpoint", is_metadata_found=True
                            )
                        )
                        self.logger.log(
                            self.fuji.LOG_SUCCESS,
                            f"{self.metric_identifier} : Found RDF content through SPARQL endpoint",
                        )
                        self.setEvaluationCriteriumScore("FsF-I1-01M-2", 1, "pass")
                        self.fuji.namespace_uri.extend(sparql_provider.getNamespaces())
                    else:
                        self.logger.warning(
                            f"{self.metric_identifier} : NO RDF metadata retrieved through the sparql endpoint"
                        )
                else:
                    self.logger.warning(
                        "{} : NO SPARQL endpoint found through re3data based on the object URI provided".format(
                            self.metric_identifier
                        )
                    )
            if test_status:
                self.score.earned += self.getTestConfigScore(self.metric_identifier + "-2")
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + "-2")
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")

        return test_status

    def evaluate(self):
        self.result = FormalMetadata(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )

        test_status = "fail"

        # note: 'source' allowed values = ["typed_link", "content_negotiate", "structured_data", "sparql_endpoint"]

        if self.testEmbeddedStructuredMetadataAvailable():
            test_status = "pass"
        if self.testExternalStructuredMetadataAvailable():
            test_status = "pass"
        self.result.test_status = test_status
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.output = self.outputs
