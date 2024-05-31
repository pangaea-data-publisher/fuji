# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

import fuji_server.models.fair_results
from fuji_server.helper.metadata_mapper import Mapper

DQV = Namespace("http://www.w3.org/ns/dqv#")
PROV = Namespace("http://www.w3.org/ns/prov#")
QB = Namespace("http://purl.org/linked-data/cube#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
EVAL = Namespace("http://purl.org/net/EvaluationResult#")
EARL = Namespace("http://www.w3.org/ns/earl#")
OA = Namespace("http://www.w3.org/ns/oa#")
SDMXATT = Namespace("http://purl.org/linked-data/sdmx/2009/attribute#")


class FAIRResultsMapper:
    # a class which allows to map the results dict to various (non JSON) output formats
    # initially only RDF style outputs are allowed
    allowed_serialisations = {
        "application/rdf+xml": "xml",
        "application/x-turtle": "ttl",
        "text/turtle": "ttl",
        "application/ld+json": "json-ld",
        "text/n3": "n3",
    }

    def __init__(self, result):
        self.maturity_levels = Mapper.MATURITY_LEVELS.value
        self.result = {}
        fuji_tester_id = "https://f-uji.net/test"
        self.fuji_uri = URIRef(fuji_tester_id)
        self.g = Graph()
        self.g.bind("dqv", DQV)
        self.g.bind("eval", EVAL)
        self.g.bind("earl", EARL)
        self.g.bind("dcat", DCAT)
        self.g.bind("qb", QB)
        self.g.bind("oa", OA)
        self.g.bind("prov", PROV)
        self.g.bind("sdmxatt", SDMXATT)
        if isinstance(result, fuji_server.models.fair_results.FAIRResults):
            self.result = result
            self.result_uri = URIRef("urn:uuid:" + self.result.test_id)
            self.activity_uri = URIRef("urn:f-uji:assessement_activity:" + self.result.test_id)
            self.metrics_uri = (
                "https://f-uji.net/metrics/" + str(self.result.metric_version).replace("metrics_v", "") + "/"
            )

    def getQualityVocabularyRDF(self, rdf_mime):
        rdf = ""
        if rdf_mime in self.allowed_serialisations:
            if self.result:
                assessed_dataset_uri = self.result.request.get("object_identifier")
                summary_scores_percent = self.result.summary.get("score_percent")
                summary_maturity = self.result.summary.get("maturity")
                # summary_scores_earned = self.result.summary.get("score_earned")
                FMET = Namespace(self.metrics_uri + "/")
                FRSC = Namespace("urn:uuid:" + self.result.test_id + ":")
                self.g.bind("fmet", FMET)
                self.g.bind("frsc", FRSC)
                # result/dataset metadata
                self.g.add((self.result_uri, RDF.type, DQV.QualityMetadata))
                self.g.add((self.result_uri, RDF.type, DCAT.Dataset))
                self.g.add((self.result_uri, RDF.type, QB.Dataset))
                self.g.add((self.result_uri, PROV.generatedAtTime, Literal(self.result.end_timestamp)))
                self.g.add((self.result_uri, DCTERMS.creator, Literal("F-UJI")))
                self.g.add((self.result_uri, DCTERMS.subject, Literal("data quality")))
                self.g.add((self.result_uri, DCTERMS.subject, Literal("FAIR")))

                self.g.add(
                    (
                        self.result_uri,
                        DCTERMS.title,
                        Literal(
                            "FAIR assessment results for digital object identified by: " + str(assessed_dataset_uri)
                        ),
                    )
                )
                self.g.add(
                    (
                        self.result_uri,
                        DCTERMS.description,
                        Literal(
                            "This dataset contains the results of an automated FAIR assessment for digital objects performed by the F-UJI tool, version "
                            + str(self.result.software_version)
                            + ""
                            " In this dataset, the digital resource identified by " + str(assessed_dataset_uri) + ""
                            " was checked for FAIRness using the FAIRsFAIR "
                            + str(self.result.metric_version)
                            + " metric."
                            "The results may have been influenced by a variety of factors, in particular the accessibility of the resource itself and the availability of external web services at the time of the assessment."
                        ),
                    )
                )
                self.g.add((self.result_uri, DCTERMS.rights, URIRef("http://purl.org/eprint/accessRights/OpenAccess")))
                self.g.add((self.result_uri, DCTERMS.issued, Literal(self.result.end_timestamp)))
                self.g.add((self.result_uri, DCTERMS.identifier, self.result_uri))
                self.g.add(
                    (self.result_uri, DCTERMS.publisher, Literal("F-UJI FAIR assessment web publishing service"))
                )
                self.g.add(
                    (self.result_uri, DCTERMS.license, URIRef("https://creativecommons.org/publicdomain/zero/1.0/"))
                )
                self.g.add((self.result_uri, DCTERMS.source, URIRef(assessed_dataset_uri)))

                # activity
                self.g.add((self.activity_uri, RDF.type, PROV.Activity))
                self.g.add((self.activity_uri, PROV.wasAssociatedWith, self.fuji_uri))
                self.g.add((self.activity_uri, PROV.generated, self.result_uri))
                self.g.add((self.activity_uri, PROV.used, URIRef(assessed_dataset_uri)))
                self.g.add((self.activity_uri, PROV.startedAtTime, Literal(self.result.start_timestamp)))

                # agent
                self.g.add((self.fuji_uri, RDF.type, PROV.SoftwareAgent))
                self.g.add((self.fuji_uri, RDF.type, PROV.Agent))
                self.g.add((self.fuji_uri, RDFS.label, Literal("F-UJI an automated FAIR assessment tool")))
                self.g.add((self.fuji_uri, OWL.versionInfo, Literal(str(self.result.software_version))))

                # overall FAIR
                total_fair_maturity = self.maturity_levels.get(round(float(summary_maturity.get("FAIR")), 0))
                self.g.add((FRSC["FsF-FAIR"], RDF.type, DQV.QualityMeasurement))
                self.g.add((FRSC["FsF-FAIR"], RDF.type, EVAL.QualityValue))
                self.g.add((FRSC["FsF-FAIR"], RDF.type, DQV.QualityAnnotation))
                self.g.add((FRSC["FsF-FAIR"], DQV.isMeasurementOf, FMET["FsF-FAIR"]))
                self.g.add((FRSC["FsF-FAIR"], QB.dataSet, self.result_uri))
                self.g.add((FRSC["FsF-FAIR"], DQV.computedOn, URIRef(assessed_dataset_uri)))
                self.g.add(
                    (
                        FRSC["FsF-FAIR"],
                        DQV.value,
                        Literal(round(float(summary_scores_percent.get("FAIR")), 2), datatype=XSD.float),
                    )
                )
                self.g.add(
                    (
                        FRSC["FsF-FAIR"],
                        SDMXATT.unitMeasure,
                        URIRef("http://www.wurvoc.org/vocabularies/om-1.8/Percentage_unit"),
                    )
                )
                self.g.add((FRSC["FsF-FAIR"], EVAL.hasLiteralValue, Literal(total_fair_maturity)))
                self.g.add((FRSC["FsF-FAIR"], EVAL.evaluatedSubject, URIRef(assessed_dataset_uri)))
                self.g.add((FRSC["FsF-FAIR"], EVAL.forMeasure, FMET["FsF-FAIR"]))
                self.g.add((FRSC["FsF-FAIR"], EVAL.isMeasuredOnScale, FMET["MaturityScale"]))
                #   quality annotation
                self.g.add((FRSC["FsF-FAIR"], OA.hasTarget, self.result_uri))
                self.g.add((FRSC["FsF-FAIR"], OA.motivatedBy, DQV.qualityAssessment))
                self.g.add((FRSC["FsF-FAIR"], OA.bodyValue, Literal(total_fair_maturity)))

                for metric_result in self.result.results:
                    metric_string = str(metric_result.get("metric_identifier")).replace(".", "_")
                    # print(metric_result)
                    metric_result_log = metric_result.get("test_debug")
                    print(metric_result_log)
                    metric_result_id = FRSC[metric_string]
                    metric_identifier = FMET[metric_string]
                    metric_passed_or_failed = metric_result.get("test_status") + "ed"
                    metric_fair_maturity = self.maturity_levels.get(round(float(metric_result.get("maturity")), 0))
                    self.g.add((metric_result_id, RDF.type, DQV.QualityMeasurement))
                    self.g.add((metric_result_id, RDF.type, EARL.Assertion))
                    self.g.add((metric_result_id, RDF.type, DQV.QualityAnnotation))
                    self.g.add((metric_result_id, RDF.type, EVAL.QualityValue))
                    self.g.add((metric_result_id, DQV.isMeasurementOf, metric_identifier))
                    self.g.add((metric_result_id, SKOS.broader, FRSC["FsF-FAIR"]))
                    self.g.add((metric_result_id, QB.dataSet, self.result_uri))
                    self.g.add((metric_result_id, QB.computedOn, URIRef(assessed_dataset_uri)))
                    metric_result_score = metric_result.get("score")
                    if metric_result_score:
                        if float(metric_result_score.get("earned")) > 0:
                            metric_percent_score = round(
                                float(metric_result_score.get("earned"))
                                / float(metric_result_score.get("total"))
                                * 100,
                                2,
                            )
                        else:
                            metric_percent_score = 0
                        self.g.add((metric_result_id, DQV.value, Literal(metric_percent_score, datatype=XSD.float)))
                        self.g.add(
                            (
                                metric_result_id,
                                SDMXATT.unitMeasure,
                                URIRef("http://www.wurvoc.org/vocabularies/om-1.8/Percentage_unit"),
                            )
                        )
                        self.g.add((metric_result_id, EVAL.hasLiteralValue, Literal(metric_fair_maturity)))
                        self.g.add((metric_result_id, EVAL.forMeasure, metric_identifier))
                        self.g.add((metric_result_id, EVAL.isMeasuredOnScale, FMET.MaturityScale))
                        self.g.add((metric_result_id, OA.hasTarget, URIRef(assessed_dataset_uri)))
                        self.g.add((metric_result_id, OA.motivatedBy, DQV.qualityAssessment))
                        self.g.add((metric_result_id, OA.bodyValue, Literal(metric_fair_maturity)))
                        metric_earl_node = BNode()
                        # metric_earl_node = URIRef(FRSC[metric_string + '_earl_result'])
                        self.g.add((metric_earl_node, RDF.type, EARL.outcome))
                        self.g.add((metric_earl_node, EARL.result, EARL[metric_passed_or_failed]))
                        self.g.add((metric_result_id, EARL.result, metric_earl_node))
                        self.g.add((metric_result_id, EARL.test, metric_identifier))
                        if isinstance(metric_result_log, list):
                            self.g.add((metric_result_id, EARL.info, Literal("\n".join(metric_result_log))))
                        metric_results_derived_from = []
                        for metric_test_string, metric_test_result in metric_result.get("metric_tests").items():
                            metric_test_string = str(metric_test_string).replace(".", "_")
                            metric_test_result_id = FRSC[metric_test_string]
                            metric_test_identifier = FMET[metric_test_string]
                            metric_results_derived_from.append(metric_test_identifier)
                            metric_test_passed_or_failed = metric_test_result.get("metric_test_status") + "ed"
                            self.g.add((metric_test_result_id, RDF.type, DQV.QualityMeasurement))
                            self.g.add((metric_test_result_id, RDF.type, EARL.Assertion))
                            self.g.add((metric_test_result_id, SKOS.broader, metric_identifier))
                            self.g.add((metric_test_result_id, DQV.isMeasurementOf, metric_test_identifier))
                            self.g.add((metric_test_result_id, QB.dataSet, self.result_uri))
                            self.g.add((metric_test_result_id, QB.computedOn, URIRef(assessed_dataset_uri)))
                            self.g.add(
                                (
                                    metric_test_result_id,
                                    DQV.value,
                                    Literal(round(float(metric_test_result.get("metric_test_score").get("earned")), 1)),
                                )
                            )
                            # earl
                            metric_test_earl_node = BNode()
                            self.g.add((metric_test_earl_node, RDF.type, EARL.outcome))
                            self.g.add((metric_test_earl_node, EARL.result, EARL[metric_test_passed_or_failed]))
                            self.g.add((metric_test_result_id, EARL.result, metric_test_earl_node))
                            self.g.add((metric_test_result_id, EARL.test, metric_test_identifier))
                        if metric_results_derived_from:
                            for derived_from_test in metric_results_derived_from:
                                self.g.add((metric_result_id, PROV.wasDerivedFrom, derived_from_test))

                rdf = self.g.serialize(format=self.allowed_serialisations.get(rdf_mime))
                print(rdf, self.allowed_serialisations.get(rdf_mime))
        return rdf
