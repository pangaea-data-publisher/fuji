# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import json
import re

import idutils
import jmespath
import rdflib
import requests
from pyld import jsonld
from rdflib import Namespace
from rdflib.namespace import (
    DC,
    DCTERMS,
    FOAF,
    RDF,
    SDO,  # schema.org
)

from fuji_server.helper.metadata_collector import MetaDataCollector, MetadataFormats, MetadataSources
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.request_helper import AcceptTypes, RequestHelper


class MetaDataCollectorRdf(MetaDataCollector):
    """
    A class to collect the metadata given the Resource Description Framework (RDF) graph. This class is child class of MetadataCollector.

    ...

    Attributes
    ----------
    source_name : str
        Source name of metadata
    target_url : str
        Target URL of the metadata
    content_type : str
        Content type of HTTP response
    rdf_graph : rdflib.ConjunctiveGraph
        An object of RDF graph

    Methods
    --------
    parse_metadata()
        Method to parse the metadata given RDF graph
    get_default_metadata(g)
        Method to get the default metadata given RDF graph
    get_metadata(g, item, type='Dataset')
        Method to get the core metadata in RDF graph
    get_ontology_metadata(graph)
        Method to get ontology by matching the type of IRI into OWL or SKOS class in the RDF graph
    get_dcat_metadata(graph)
        Method to get Data Catalog(DCAT) metadata in RDF graph
    get_content_type()
        Method to get the content type attribute in the class
    get_metadata_from_graph(g)
        Method to get all metadata from a graph object
    """

    target_url = None
    SCHEMA_ORG_CONTEXT = Preprocessor.get_schema_org_context()
    SCHEMA_ORG_CREATIVEWORKS = Preprocessor.get_schema_org_creativeworks()

    def __init__(self, loggerinst, target_url=None, source=None, json_ld_content=None):
        """
        Parameters
        ----------
        source : str
            Source of metadata
        loggerinst : logging.Logger
            Logger instance
        target_url : str
            Target URL
        rdf_graph : rdflib.ConjunctiveGraph, optional
            RDF graph, default=None
        """
        super().__init__(logger=loggerinst)

        self.target_url = target_url
        self.resolved_url = target_url
        self.content_type = None
        self.source_name = source
        self.metadata_format = MetadataFormats.RDF
        if self.source_name == MetadataSources.RDFA_EMBEDDED:
            self.metadata_format = MetadataFormats.RDFA
        self.json_ld_content = json_ld_content
        # self.rdf_graph = rdf_graph
        self.accept_type = AcceptTypes.rdf

    def getAllURIS(self, graph):
        founduris = []
        for link in list(graph.objects()):
            if isinstance(link, rdflib.term.URIRef):
                founduris.append(str(link))
        return founduris

    def set_namespaces(self, graph):
        namespaces = {}
        known_namespace_regex = [
            r"https?:\/\/vocab\.nerc\.ac\.uk\/collection\/[A-Z][0-9]+\/current\/",
            r"https?:\/\/purl\.obolibrary\.org\/obo\/[a-z]+(\.owl|#)",
        ]
        try:
            nm = graph.namespace_manager
            possible = set(graph.predicates()).union(graph.objects(None, RDF.type))
            alluris = set(graph.objects()).union(set(graph.subjects()))
            # namespaces from mentioned objects and subjects uris (best try)
            for uri in alluris:
                if idutils.is_url(uri):
                    for known_pattern in known_namespace_regex:
                        kpm = re.match(known_pattern, uri)
                        if kpm:
                            uri = kpm[0]
                            self.namespaces.append(uri)
                        else:
                            uri = str(uri).strip().rstrip("/#")
                            if "#" in uri:
                                namespace_candidate = uri.rsplit("#", 1)[0]
                            else:
                                namespace_candidate = uri.rsplit("/", 1)[0]
                            if namespace_candidate != uri:
                                self.namespaces.append(namespace_candidate)
                            else:
                                namespace_candidate = uri.rsplit("#", 1)[0]
                                if namespace_candidate != uri:
                                    self.namespaces.append(namespace_candidate)
            # defined namespaces
            for predicate in possible:
                prefix, namespace, local = nm.compute_qname(predicate)
                namespaces[prefix] = namespace
                self.namespaces.append(str(namespace))
            self.namespaces = list(set(self.namespaces))

        except Exception as e:
            self.logger.info(f"FsF-F2-01M : RDF Namespace detection error -: {e}")
        return namespaces

    def get_metadata_from_graph(self, rdf_response_graph):
        rdf_metadata = {}
        if rdf_response_graph:
            ontology_indicator = [
                rdflib.term.URIRef("http://www.w3.org/2004/02/skos/core#"),
                rdflib.term.URIRef("http://www.w3.org/2002/07/owl#"),
            ]
            if isinstance(rdf_response_graph, rdflib.graph.Graph) or isinstance(rdflib.graph.ConjunctiveGraph):
                self.logger.info("FsF-F2-01M : Found RDF Graph which was sucessfully parsed")
                self.logger.info("FsF-F2-01M : Trying to identify namespaces in RDF Graph")
                graph_namespaces = self.set_namespaces(rdf_response_graph)
                # self.getNamespacesfromIRIs(graph_text)
                schema_metadata, dcat_metadata, skos_metadata = {}, {}, {}
                if rdflib.term.URIRef("http://www.w3.org/ns/dcat#") in graph_namespaces.values():
                    self.logger.info("FsF-F2-01M : RDF Graph seems to contain DCAT metadata elements")
                    dcat_metadata = self.get_dcat_metadata(rdf_response_graph)
                if (
                    rdflib.term.URIRef("http://schema.org/") in graph_namespaces.values()
                    or rdflib.term.URIRef("https://schema.org/") in graph_namespaces.values()
                ):
                    self.logger.info("FsF-F2-01M : RDF Graph seems to contain schema.org metadata elements")
                    schema_metadata = self.get_schemaorg_metadata_from_graph(rdf_response_graph)
                if bool(set(ontology_indicator) & set(graph_namespaces.values())):
                    self.logger.info("FsF-F2-01M : RDF Graph seems to contain SKOS/OWL metadata elements")
                    skos_metadata = self.get_ontology_metadata(rdf_response_graph)
                # merging metadata dicts
                rdf_metadata = skos_metadata | dcat_metadata | schema_metadata
                # else:
                if not rdf_metadata:
                    self.logger.info(
                        "FsF-F2-01M : Could not find DCAT, schema.org or SKOS/OWL metadata, continuing with generic SPARQL"
                    )
                    # try to find root node
                    """
                    typed_objects = list(rdf_response_graph.objects(predicate=RDF.type))
                    if typed_objects:
                        typed_nodes = list(rdf_response_graph[:RDF.type:typed_objects[0]])
                        if typed_nodes:
                            rdf_metadata = self.get_metadata(rdf_response_graph, typed_nodes[0], str(typed_objects[0]))
                    """
                    # if not rdf_metadata or len(list(rdf_metadata)) <= 1:
                    rdf_metadata = self.get_sparqled_metadata(rdf_response_graph)

                # add found namespaces URIs to namespace
                # for ns in graph_namespaces.values():
                #    self.namespaces.append(ns)
            else:
                self.logger.info(f"FsF-F2-01M : Expected RDF Graph but received -: {self.content_type}")
        return rdf_metadata

    def parse_metadata(self):
        """Parse the metadata given RDF graph.

        Returns
        ------
        str
            a string of source name
        dict
            a dictionary of metadata in RDF graph
        """
        # self.source_name = self.getEnumSourceNames().LINKED_DATA.value
        # self.logger.info('FsF-F2-01M : Trying to request RDF metadata from -: {}'.format(self.source_name))
        rdf_metadata = dict()
        rdf_response_graph = None
        # if self.rdf_graph is None:
        if not self.json_ld_content and self.target_url:
            if not self.accept_type:
                self.accept_type = AcceptTypes.rdf
            requestHelper: RequestHelper = RequestHelper(self.target_url, self.logger)
            requestHelper.setAcceptType(self.accept_type)
            requestHelper.setAuthToken(self.auth_token, self.auth_token_type)
            neg_format, rdf_response = requestHelper.content_negotiate("FsF-F2-01M")
            self.metadata_format = neg_format
            if requestHelper.checked_content_hash:
                if (
                    requestHelper.checked_content.get(requestHelper.checked_content_hash).get("checked")
                    and "xml" in requestHelper.content_type
                ):
                    requestHelper.response_content = None
                    self.logger.info("FsF-F2-01M : Ignoring RDF since content already has been parsed as XML")
            if requestHelper.response_content is not None:
                self.content_type = requestHelper.content_type
                self.resolved_url = requestHelper.redirect_url
        else:
            self.content_type = "application/ld+json"
            rdf_response = self.json_ld_content
        if self.content_type is not None:
            self.content_type = self.content_type.split(";", 1)[0]
            # handle JSON-LD
            if self.content_type in ["application/ld+json", "application/json", "application/vnd.schemaorg.ld+json"]:
                if self.target_url:
                    jsonld_source_url = self.resolved_url
                else:
                    jsonld_source_url = "landing page"
                if self.json_ld_content:
                    self.source_name = MetadataSources.SCHEMAORG_EMBEDDED
                    self.metadata_format = MetadataFormats.JSONLD
                elif (
                    self.source_name != MetadataSources.RDF_TYPED_LINKS
                    and self.source_name != MetadataSources.RDF_SIGNPOSTING_LINKS
                ):
                    self.source_name = MetadataSources.SCHEMAORG_NEGOTIATED
                    self.metadata_format = MetadataFormats.JSONLD
                if rdf_response:
                    self.logger.info("FsF-F2-01M : Try to parse RDF (JSON-LD) from -: %s" % (jsonld_source_url))
                    if isinstance(rdf_response, bytes):
                        try:
                            rdf_response = rdf_response.decode("utf-8")
                        except:
                            pass
                    if isinstance(rdf_response, dict) or isinstance(rdf_response, list):
                        self.logger.info(
                            "FsF-F2-01M : Try to parse JSON-LD using JMESPath retrieved as dict from -: %s"
                            % (jsonld_source_url)
                        )
                        # in case two or more JSON-LD strings are embedded
                        if isinstance(rdf_response, list):
                            json_dict = None
                            if len(rdf_response) > 1:
                                self.logger.info(
                                    "FsF-F2-01M : Found more than one JSON-LD embedded in landing page try to identify Dataset or CreativeWork type"
                                )
                                for meta_rec in rdf_response:
                                    meta_rec_type = str(meta_rec.get("@type")).lower().lstrip("schema:")
                                    if meta_rec_type in ["dataset"]:
                                        json_dict = meta_rec
                                        break
                                    if meta_rec_type in self.SCHEMA_ORG_CREATIVEWORKS:
                                        json_dict = meta_rec
                            if not json_dict:
                                rdf_response = rdf_response[0]
                            else:
                                rdf_response = json_dict
                        # else:
                        #    rdf_response_dict = rdf_response
                        try:
                            # rdf_response_json = json.dumps(rdf_response_dict)
                            # rdf_metadata = self.get_schemorg_metadata_from_dict(rdf_response_dict)
                            # rdf_metadata = self.get_schemaorg_metadata_from_graph(rdf_response_json)
                            # if rdf_metadata:
                            #    self.setLinkedNamespaces(str(rdf_response))
                            # else:
                            #    self.logger.info(
                            #        "FsF-F2-01M : Could not identify schema.org JSON-LD metadata using JMESPath, continuing with RDF graph processing"
                            #    )
                            # quick fix for https://github.com/RDFLib/rdflib/issues/1484
                            # needs to be done before dict is converted to string
                            # print(rdf_response)
                            if 1 == 1:
                                if isinstance(rdf_response, dict):
                                    if rdf_response.get("@context"):
                                        if rdf_response.get("@graph"):
                                            try:
                                                # drop duplicate context in graph
                                                if isinstance(rdf_response.get("@graph"), list):
                                                    for grph in rdf_response.get("@graph"):
                                                        if grph.get("@context"):
                                                            del grph["@context"]
                                                else:
                                                    if rdf_response.get("@graph").get("@context"):
                                                        del rdf_response["@graph"]["@context"]
                                            except Exception:
                                                print("Failed drop duplicate JSON-LD context in graph")
                                                pass
                                        # Fixing Dereferencing issues: https://github.com/json-ld/json-ld.org/issues/747
                                        if isinstance(rdf_response.get("@context"), list):
                                            for ctxi, ctxt in enumerate(rdf_response.get("@context")):
                                                if "schema.org" in ctxt:
                                                    rdf_response["@context"][ctxi] = (
                                                        "https://schema.org/docs/jsonldcontext.json"
                                                    )
                                        if isinstance(rdf_response.get("@context"), str):
                                            if "schema.org" in rdf_response.get("@context"):
                                                rdf_response["@context"] = "https://schema.org/docs/jsonldcontext.json"
                                    # expand graph
                                    rdf_response = jsonld.expand(rdf_response)
                                # convert dict to json string again for RDF graph parsing
                                rdf_response = json.dumps(rdf_response)
                        except Exception as e:
                            print("RDF Collector Error: ", e)
                            pass
                    # try to make graph from JSON-LD string
                    if isinstance(rdf_response, str) and rdf_response not in ["null", "None"]:
                        try:
                            rdf_response = str(rdf_response).encode("utf-8")
                        except:
                            self.logger.info("FsF-F2-01M : UTF-8 string conversion of JSON-LD failed")
                            pass
                        self.logger.info(
                            "FsF-F2-01M : Try to parse JSON-LD using RDFLib retrieved as string from -: %s"
                            % (jsonld_source_url)
                        )
                        try:
                            jsonldgraph = rdflib.ConjunctiveGraph(identifier=self.resolved_url)
                            rdf_response_graph = jsonldgraph.parse(
                                data=rdf_response, format="json-ld", publicID=self.resolved_url
                            )
                            # rdf_response_graph = jsonldgraph
                            self.setLinkedNamespaces(self.getAllURIS(jsonldgraph))
                        except Exception as e:
                            print("JSON-LD parsing error", e, rdf_response[:100])
                            self.logger.info(f"FsF-F2-01M : Parsing error (RDFLib), failed to extract JSON-LD -: {e}")

            elif self.accept_type == AcceptTypes.rdf:
                # parse all other RDF formats (non JSON-LD schema.org)
                # parseformat = re.search(r'[\/+]([a-z0-9]+)$', str(requestHelper.content_type))
                format_dict = {
                    "text/ttl": "turtle",
                    "application/xhtml+xml": "rdfa",
                    "application/n-triples": "nt",
                    "application/n-quads": "nquads",
                }
                if self.content_type in format_dict:
                    parseformat = (None, format_dict[self.content_type])
                else:
                    parseformat = re.search(r"[\/+]([a-z0-9]+)$", str(self.content_type))
                if parseformat:
                    parse_format = parseformat[1]
                    if parse_format == "rdfa":
                        self.metadata_format = MetadataFormats.RDFA
                    if parse_format not in [
                        "xml",
                        "n3",
                        "turtle",
                        "nt",
                        "pretty-xml",
                        "trix",
                        "trig",
                        "nquads",
                        "json-ld",
                        "hext",
                    ]:
                        parse_format = "turtle"
                    if "html" not in str(parse_format) and "zip" not in str(parse_format):
                        RDFparsed = False
                        self.logger.info(f"FsF-F2-01M : Try to parse RDF from -: {self.target_url} as {parse_format}")
                        badline = None
                        while not RDFparsed:
                            try:
                                graph = rdflib.Graph(identifier=self.resolved_url)
                                graph.parse(data=rdf_response, format=parse_format)
                                rdf_response_graph = graph
                                self.setLinkedNamespaces(self.getAllURIS(rdf_response_graph))
                                RDFparsed = True
                            except Exception as e:
                                # <unknown>:74964:92: unclosed token
                                errorlinematch = re.search(r"\sline\s([0-9]+)", str(e))
                                if not errorlinematch:
                                    errorlinematch = re.search(r"<unknown>:([0-9]+)", str(e))
                                if errorlinematch and parseformat[1] != "xml":
                                    if int(errorlinematch[1]) + 1 != badline:
                                        badline = int(errorlinematch[1])
                                        self.logger.warning(
                                            "FsF-F2-01M : Failed to parse RDF, trying to fix RDF string and retry parsing everything before line -: %s "
                                            % str(badline)
                                        )
                                        splitRDF = rdf_response.splitlines()
                                        if len(splitRDF) >= 1 and badline <= len(splitRDF) and badline > 1:
                                            rdf_response = b"\n".join(splitRDF[: badline - 1])
                                        else:
                                            RDFparsed = True  # end reached
                                    else:
                                        RDFparsed = True
                                else:
                                    RDFparsed = True  # give up
                                if not RDFparsed:
                                    continue
                                else:
                                    self.logger.warning(f"FsF-F2-01M : Failed to parse RDF -: {self.target_url} {e!s}")
                    else:
                        self.logger.info(
                            "FsF-F2-01M : Seems to be HTML not RDF, therefore skipped parsing RDF from -: %s"
                            % (self.target_url)
                        )
                else:
                    self.logger.info(
                        f"FsF-F2-01M : Could not determine RDF serialisation format for -: {self.target_url}"
                    )

        if not rdf_metadata:
            rdf_metadata = self.get_metadata_from_graph(rdf_response_graph)

        return self.source_name, rdf_metadata

    def get_sparqled_metadata(self, g):
        """Get the default metadata given the RDF graph.

        Parameters
        ----------
        g : RDF.ConjunctiveGraph
            RDF Conjunctive Graph object

        Returns
        ------
        dict
            a dictionary of metadata in RDF graph
        """
        meta = dict()

        try:
            if len(g) >= 1:
                self.logger.info("FsF-F2-01M : Trying to query generic SPARQL on RDF, found triples: -:" + str(len(g)))
                r = g.query(Mapper.GENERIC_SPARQL.value)
                for row in r:
                    for row_property, row_value in row.asdict().items():
                        if row_property is not None:
                            if row_property in [
                                "references",
                                "source",
                                "isVersionOf",
                                "isReferencedBy",
                                "isPartOf",
                                "hasVersion",
                                "replaces",
                                "hasPart",
                                "citation",
                                "isReplacedBy",
                                "requires",
                                "isRequiredBy",
                            ]:
                                if not meta.get("related_resources"):
                                    meta["related_resources"] = []
                                meta["related_resources"].append(
                                    {"related_resource": str(row_value), "relation_type": row_property}
                                )
                            else:
                                if row_value:
                                    if not isinstance(row_value, rdflib.term.BNode):
                                        meta[row_property] = str(row_value)
                    if meta:
                        break
                    # break
            else:
                self.logger.warning(
                    "FsF-F2-01M : Graph seems to contain no triple, skipping core metadata element test"
                )
        except Exception as e:
            self.logger.info(f"FsF-F2-01M : SPARQLing error -: {e}")
        if len(meta) <= 0:
            goodtriples = []
            has_xhtml = False
            for t in list(g):
                # exclude xhtml properties/predicates:
                if "/xhtml/vocab" not in t[1] and "/ogp.me" not in t[1]:
                    goodtriples.append(t)
                else:
                    has_xhtml = True
            if has_xhtml:
                self.logger.info(
                    "FsF-F2-01M : Found RDFa like triples but at least some of them seem to be XHTML or OpenGraph properties which are excluded"
                )
            if len(goodtriples) > 1:
                if not meta.get("object_type"):
                    meta["object_type"] = "Other"
                self.logger.info(
                    "FsF-F2-01M : Could not find core metadata elements through generic SPARQL query on RDF but found "
                    + str(len(goodtriples))
                    + " triples in the given graph"
                )
        elif meta.get("object_type"):
            # Ignore non CreativeWork schema.org types' metadata
            if "schema.org" in meta["object_type"]:
                if meta["object_type"].split("/")[-1].lower() not in self.SCHEMA_ORG_CREATIVEWORKS:
                    self.logger.info(
                        "FsF-F2-01M : Ignoring SPARQLed metadata: seems to be non CreativeWork schema.org type: "
                        + str(meta["object_type"])
                    )
                    # ignore all metadata but keep the type
                    meta = {"object_type": meta["object_type"]}
            if meta:
                self.logger.info(
                    "FsF-F2-01M : Found some core metadata elements through generic SPARQL query on RDF -: "
                    + str(meta.keys())
                )
        return meta

    # TODO rename to: get_core_metadata
    def get_core_metadata(self, g, item, type="Dataset"):
        """Get the core (domain agnostic, DCAT, DC, schema.org) metadata given in RDF graph.

        Parameters
        ----------
        g : RDF.ConjunctiveGraph
            RDF Conjunctive Graph object
        item : Any
            item to be found the metadata
        type : str
            type of object

        Returns
        ------
        dict
            a dictionary of core metadata in RDF graph
        """
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        SMA = Namespace("http://schema.org/")
        ODLR = Namespace("http://www.w3.org/ns/odrl/2/")
        meta = dict()
        # default sparql
        # meta = self.get_default_metadata(g)
        self.logger.info(
            "FsF-F2-01M : Trying to get some core domain agnostic (DCAT, DC, schema.org) metadata from RDF graph"
        )
        if not meta.get("object_identifier"):
            meta["object_identifier"] = []
            for identifier in (
                list(g.objects(item, DC.identifier))
                + list(g.objects(item, DCTERMS.identifier))
                + list(g.objects(item, SDO.identifier))
                + list(g.objects(item, SMA.identifier))
                + list(g.objects(item, SDO.sameAs))
                + list(g.objects(item, SMA.sameAs))
                + list(g.objects(item, SMA.url))
                + list(g.objects(item, SDO.url))
            ):
                idvalue = g.value(identifier, SDO.value) or g.value(identifier, SMA.value)
                if idvalue:
                    identifier = idvalue
                meta["object_identifier"].append(str(identifier))
        if not meta.get("language"):
            meta["language"] = str(
                g.value(item, DC.language)
                or g.value(item, DCTERMS.language)
                or g.value(item, SDO.inLanguage)
                or g.value(item, SMA.inLanguage)
            )
        if not meta.get("title"):
            meta["title"] = str(
                g.value(item, DC.title)
                or g.value(item, DCTERMS.title)
                or g.value(item, SMA.name)
                or g.value(item, SDO.name)
                or g.value(item, SMA.headline)
                or g.value(item, SDO.headline)
            )
        if not meta.get("summary"):
            meta["summary"] = str(
                g.value(item, DC.description)
                or g.value(item, DCTERMS.description)
                or g.value(item, DCTERMS.abstract)
                or g.value(item, SMA.description)
                or g.value(item, SDO.description)
                or g.value(item, SMA.abstract)
                or g.value(item, SDO.abstract)
            )
        if not meta.get("publication_date"):
            meta["publication_date"] = str(
                g.value(item, DC.date)
                or g.value(item, DCTERMS.date)
                or g.value(item, DCTERMS.issued)
                or g.value(item, SMA.datePublished)
                or g.value(item, SMA.dateCreated)
                or g.value(item, SDO.datePublished)
                or g.value(item, SDO.dateCreated)
            )
        if not meta.get("publisher"):
            meta["publisher"] = []
            for publisher in (
                list(g.objects(item, DC.publisher))
                or list(g.objects(item, DCTERMS.publisher))
                or list(g.objects(item, SMA.publisher))
                or list(g.objects(item, SDO.publisher))
                or list(g.objects(item, SMA.provider))
                or list(g.objects(item, SDO.provider))
            ):
                publishername = (
                    g.value(publisher, FOAF.name) or (g.value(publisher, SMA.name)) or (g.value(publisher, SDO.name))
                )
                publisheruri = (
                    g.value(publisher, FOAF.homepage) or (g.value(publisher, SMA.url)) or (g.value(publisher, SDO.url))
                )
                if publisheruri:
                    meta["publisher"].append(str(publisheruri))
                if publishername:
                    meta["publisher"].append(str(publishername))
                if not meta.get("publisher"):
                    meta["publisher"].append(str(publisher))
            # meta['publisher'] = str(g.value(item, DC.publisher) or g.value(item, DCTERMS.publisher) or
            #                     g.value(item, SMA.publisher) or g.value(item, SDO.publisher) or g.value(item, SMA.provider) or g.value(item, SDO.provider))
        if not meta.get("keywords"):
            meta["keywords"] = []
            for keyword in (
                list(g.objects(item, DCAT.keyword))
                + list(g.objects(item, DCTERMS.subject))
                + list(g.objects(item, DC.subject))
                or list(g.objects(item, SMA.keywords))
                or list(g.objects(item, SDO.keywords))
            ):
                meta["keywords"].append(str(keyword))
        # TODO creators, contributors
        if not meta.get("creator"):
            meta["creator"] = []
            for creator in (
                list(g.objects(item, DCTERMS.creator))
                or list(g.objects(item, DC.creator))
                or list(g.objects(item, SMA.author))
            ):
                if g.value(creator, FOAF.name):
                    meta["creator"].append(str(g.value(creator, FOAF.name)))
                else:
                    meta["creator"].append(str(creator))

        if not meta.get("contributor"):
            meta["contributor"] = []
            for contributor in (
                list(g.objects(item, DCTERMS.contributor))
                or list(g.objects(item, DC.contributor))
                or list(g.objects(item, SMA.contributor))
            ):
                meta["contributor"].append(str(contributor))

        if not meta.get("license"):
            license_item = g.value(item, DCTERMS.license) or g.value(item, SDO.license) or g.value(item, SMA.license)
            # schema.org
            license_value = str(license_item)
            if g.value(license_item, SDO.url) or g.value(license_item, SMA.url):
                license_value = g.value(license_item, SDO.url) or g.value(license_item, SMA.url)
            meta["license"] = str(license_value)
        if not meta.get("access_level"):
            meta["access_level"] = str(
                g.value(item, DCTERMS.accessRights)
                or g.value(item, DCTERMS.rights)
                or g.value(item, DC.rights)
                or g.value(item, ODLR.hasPolicy)
                or g.value(item, SDO.conditionsOfAccess)
                or g.value(item, SMA.conditionsOfAccess)
            )
        if not meta.get("related_resources"):
            meta["related_resources"] = []
            for dctrelationtype in [
                DCTERMS.references,
                DCTERMS.source,
                DCTERMS.isVersionOf,
                DCTERMS.isReferencedBy,
                DCTERMS.isPartOf,
                DCTERMS.hasVersion,
                DCTERMS.replaces,
                DCTERMS.hasPart,
                DCTERMS.isReplacedBy,
                DCTERMS.requires,
                DCTERMS.isRequiredBy,
            ]:
                dctrelation = g.value(item, dctrelationtype)
                if dctrelation:
                    meta["related_resources"].append(
                        {"related_resource": str(dctrelation), "relation_type": str(dctrelationtype)}
                    )
            for schemarelationtype in [
                SMA.isPartOf,
                SMA.includedInDataCatalog,
                SMA.subjectOf,
                SMA.isBasedOn,
                SMA.sameAs,
                SMA.citation,
                SDO.isPartOf,
                SDO.includedInDataCatalog,
                SDO.subjectOf,
                SDO.isBasedOn,
                SDO.sameAs,
                SDO.citation,
            ]:
                schemarelation = g.value(item, schemarelationtype)
                if schemarelation:
                    meta["related_resources"].append(
                        {"related_resource": str(schemarelation), "relation_type": str(schemarelationtype)}
                    )

        if meta:
            meta["object_type"] = type
            meta = {k: v for k, v in meta.items() if v not in [None, "None", []]}
            self.logger.info(
                "FsF-F2-01M : Found some core domain agnostic (DCAT, DC, schema.org) metadata from RDF graph -: "
                + str(meta)
            )
        return meta

    def get_ontology_metadata(self, graph):
        """Get the ontology given RDF graph.

        Parameters
        ----------
        graph : RDF.ConjunctiveGraph
            RDF Conjunctive Graph object

        Returns
        ------
        dict
            a dictionary of Ontology in RDF graph
        """
        ont_metadata = dict()
        OWL = Namespace("http://www.w3.org/2002/07/owl#")
        SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
        ontologies = list(graph[: RDF.type : OWL.Ontology])
        if len(ontologies) > 0:
            self.logger.info("FsF-F2-01M : RDF Graph seems to represent a OWL Ontology")
            ont_metadata = self.get_core_metadata(graph, ontologies[0], type="DefinedTermSet")
        else:
            ontologies = list(graph[: RDF.type : SKOS.ConceptScheme]) or list(graph[: RDF.type : SKOS.Collection])
            if len(ontologies) > 0:
                self.logger.info("FsF-F2-01M : RDF Graph seems to represent a SKOS Ontology")
                ont_metadata = self.get_core_metadata(graph, ontologies[0], type="DefinedTermSet")
            else:
                self.logger.info("FsF-F2-01M : Could not parse Ontology RDF")
        return ont_metadata

    def get_schemorg_metadata_from_dict(self, json_dict):
        jsnld_metadata = {}
        trusted = True
        if isinstance(json_dict, dict):
            self.logger.info(
                f"FsF-F2-01M : Trying to extract schema.org JSON-LD metadata from -: {self.source_name.name}"
            )
            # TODO check syntax - not ending with /, type and @type
            # TODO (important) extend mapping to detect other pids (link to related entities)?
            try:
                jsoncontext = []
                # if ext_meta['@context'] in check_context_type['@context'] and ext_meta['@type'] in check_context_type["@type"]:
                if str(json_dict.get("@context")).find("://schema.org") > -1:
                    schemaorgns = "schema"
                    if isinstance(json_dict.get("@context"), dict):
                        for contextname, contexturi in json_dict.get("@context").items():
                            if contexturi.endswith("schema.org/"):
                                schemaorgns = contextname
                            else:
                                jsoncontext.append(contexturi)
                    elif isinstance(json_dict.get("@context"), list):
                        for lcontext in json_dict.get("@context"):
                            if isinstance(lcontext, str):
                                jsoncontext.append(lcontext)
                            elif isinstance(lcontext, dict):
                                for lck, lcuri in lcontext.items():
                                    jsoncontext.append(lcuri)
                    json_dict = json.loads(json.dumps(json_dict).replace('"' + schemaorgns + ":", '"'))
                    # special case #1
                    if json_dict.get("mainEntity"):
                        self.logger.info(
                            "FsF-F2-01M : 'MainEntity' detected in JSON-LD, trying to identify its properties"
                        )
                        for mainEntityprop in json_dict.get("mainEntity"):
                            if isinstance(json_dict.get("mainEntity"), dict):
                                json_dict[mainEntityprop] = json_dict.get("mainEntity").get(mainEntityprop)
                    # special case #2
                    # if json_dict.get('@graph'):
                    #    self.logger.info('FsF-F2-01M : Seems to be a JSON-LD graph, trying to compact')
                    # ext_meta = self.compact_jsonld(ext_meta)

                    if not isinstance(json_dict.get("@type"), list):
                        json_dict["@type"] = [json_dict.get("@type")]

                    if not json_dict.get("@type"):
                        self.logger.info(
                            "FsF-F2-01M : Found JSON-LD which seems to be a schema.org object but has no context type"
                        )
                    elif not any(tt.lower().split("/")[-1] in self.SCHEMA_ORG_CONTEXT for tt in json_dict.get("@type")):
                        # elif str(json_dict.get('@type')).lower() not in self.SCHEMA_ORG_CONTEXT:
                        trusted = False
                        self.logger.info(
                            "FsF-F2-01M : Found JSON-LD but will not use it since it seems not to be a schema.org object based on the given context type -:"
                            + str(json_dict.get("@type"))
                        )
                    elif not any(
                        tt.lower().split("/")[-1] in self.SCHEMA_ORG_CREATIVEWORKS for tt in json_dict.get("@type")
                    ):
                        # elif str(json_dict.get('@type')).lower() not in self.SCHEMA_ORG_CREATIVEWORKS:
                        trusted = False
                        self.logger.info(
                            "FsF-F2-01M : Found schema.org JSON-LD but will not use it since it seems not to be a CreativeWork like research data object -:"
                            + str(json_dict.get("@type"))
                        )
                    else:
                        self.logger.info(
                            "FsF-F2-01M : Found schema.org JSON-LD which seems to be valid, based on the given context type -:"
                            + str(json_dict.get("@type"))
                        )
                        self.namespaces.append("http://schema.org/")
                        if jsoncontext:
                            self.namespaces.extend(jsoncontext)
                        self.namespaces = list(set(self.namespaces))

                        jsnld_metadata = jmespath.search(Mapper.SCHEMAORG_MAPPING.value, json_dict)
                    if jsnld_metadata.get("creator") is None:
                        first = jsnld_metadata.get("creator_first")
                        last = jsnld_metadata.get("creator_last")
                        if last:
                            if isinstance(first, list) and isinstance(last, list):
                                if len(first) == len(last):
                                    names = [str(i) + " " + str(j) for i, j in zip(first, last)]
                                    jsnld_metadata["creator"] = names
                            else:
                                jsnld_metadata["creator"] = [str(first) + " " + str(last)]

                    invalid_license = False
                    if jsnld_metadata.get("license"):
                        self.logger.info(
                            "FsF-R1.1-01M : License metadata found (schema.org) -: {}".format(
                                jsnld_metadata.get("license")
                            )
                        )
                        if not isinstance(jsnld_metadata.get("license"), list):
                            jsnld_metadata["license"] = [jsnld_metadata["license"]]
                        lk = 0
                        for licence in jsnld_metadata.get("license"):
                            if isinstance(licence, dict):
                                ls_type = licence.get("@type")
                                # license can be of type URL or CreativeWork
                                if ls_type == "CreativeWork":
                                    ls = licence.get("url")
                                    if not ls:
                                        ls = licence.get("name")
                                    if ls:
                                        jsnld_metadata["license"][lk] = ls
                                    else:
                                        invalid_license = True
                                else:
                                    invalid_license = True
                                if invalid_license:
                                    self.logger.warning(
                                        "FsF-R1.1-01M : Looks like schema.org representation of license is incorrect."
                                    )
                                    jsnld_metadata["license"][lk] = None
                            lk += 1

                    # filter out None values of related_resources

                    if jsnld_metadata.get("related_resources"):
                        relateds = [d for d in jsnld_metadata["related_resources"] if d["related_resource"] is not None]
                        if relateds:
                            jsnld_metadata["related_resources"] = relateds
                            self.logger.info(
                                "FsF-I3-01M : {} related resource(s) extracted from -: {}".format(
                                    len(jsnld_metadata["related_resources"]), self.source_name.name
                                )
                            )
                        else:
                            del jsnld_metadata["related_resources"]
                            self.logger.info("FsF-I3-01M : No related resource(s) found in Schema.org metadata")

                    if jsnld_metadata.get("object_size"):
                        if isinstance(jsnld_metadata["object_size"], dict):
                            jsnld_metadata["object_size"] = str(jsnld_metadata["object_size"].get("value"))
                else:
                    self.logger.info(
                        "FsF-F2-01M : Found JSON-LD but record is not of type schema.org based on context -: "
                        + str(json_dict.get("@context"))
                    )

            except Exception as err:
                # print(err.with_traceback())
                self.logger.info(f"FsF-F2-01M : Failed to parse JSON-LD schema.org -: {err}")
        else:
            self.logger.info("FsF-F2-01M : Could not identify JSON-LD schema.org metadata from ingested JSON dict")

        if not trusted:
            jsnld_metadata = {}
        return jsnld_metadata

    def find_root_candidates(self, graph, allowed_types=["Dataset"]):
        allowed_types = [at.lower() for at in allowed_types if isinstance(at, str)]
        cand_creative_work = {}
        object_types_dict = {}
        try:
            for root in rdflib.util.find_roots(graph, RDF.type):
                # we have https and http as allowed schema.org namespace protocols

                if "schema.org" in str(root):
                    root_name = str(root).rsplit("/")[-1].strip()
                elif "dcat" in str(root):
                    root_name = str(root).rsplit("#")[-1].strip()
                else:
                    root_name = None
                if root_name:
                    if root_name.lower() in allowed_types:
                        creative_works = list(graph[: RDF.type : root])
                        # Finding the schema.org root
                        creative_work_subjects = list(graph.subjects(object=creative_works[0]))
                        # don't list yourself...
                        creative_work_subjects = [crs for crs in creative_work_subjects if crs != creative_works[0]]
                        if len(creative_work_subjects) == 0:
                            cand_creative_work[root_name] = creative_works[0]
                            if object_types_dict.get(str(creative_works[0])):
                                object_types_dict[str(creative_works[0])].append(root_name)
                            else:
                                object_types_dict[str(creative_works[0])] = [root_name]
                        # root in case graph id = subject id, assuming this means: isabout
                        # helps for ro crate
                        elif graph.identifier in creative_work_subjects:
                            cand_creative_work[root_name] = creative_works[0]
        except Exception as ee:
            print("ROOT IDENTIFICATION ERROR: ", ee)
        return cand_creative_work, object_types_dict

    def get_schemaorg_metadata_from_graph(self, graph):
        # we will only test creative works and subtypes
        creative_work_types = Preprocessor.get_schema_org_creativeworks()
        creative_work = None
        schema_metadata = {}
        SMA = Namespace("http://schema.org/")
        # use only schema.org properties and create graph using these.
        # is e.g. important in case schema.org is encoded as RDFa and variuos namespaces are used
        creative_work_type = "Dataset"
        try:
            cand_creative_work, object_types_dict = self.find_root_candidates(graph, creative_work_types)
            if cand_creative_work:
                # prioritize Dataset type
                if "Dataset" in cand_creative_work:
                    creative_work = cand_creative_work["Dataset"]
                else:
                    creative_work = cand_creative_work[next(iter(cand_creative_work))]
                    creative_work_type = next(iter(cand_creative_work))

        except Exception as e:
            self.logger.info("FsF-F2-01M : Schema.org RDF graph parsing failed -: " + str(e))
            print("Cand Creative work identification Error", e)
        if creative_work:
            schema_metadata = self.get_core_metadata(graph, creative_work, type=creative_work_type)
            # object type (in case there are more than one
            if isinstance(object_types_dict.get(str(creative_work)), list):
                schema_metadata["object_type"] = object_types_dict.get(str(creative_work))
            # "access_free"
            access_free = graph.value(creative_work, SMA.isAccessibleForFree) or graph.value(
                creative_work, SDO.isAccessibleForFree
            )
            if access_free:
                schema_metadata["access_free"] = access_free
            # object size (total)

            object_size = graph.value(creative_work, SMA.size) or graph.value(creative_work, SDO.size)
            if object_size:
                size_value = graph.value(object_size, SMA.value) or graph.value(object_size, SDO.value)
                if not size_value:
                    size_value = object_size
                schema_metadata["object_size"] = size_value
            # creator
            creator_node = None
            if graph.value(creative_work, SMA.creator):
                creator_node = SMA.creator
            elif graph.value(creative_work, SDO.creator):
                creator_node = SDO.creator
            elif graph.value(creative_work, SMA.author):
                creator_node = SMA.author
            elif graph.value(creative_work, SDO.author):
                creator_node = SDO.author

            if creator_node:
                creators = graph.objects(creative_work, creator_node)
                creator_name = []
                for creator in creators:
                    creator_name.append(
                        graph.value(creator, SMA.familyName)
                        or graph.value(creator, SDO.familyName)
                        or graph.value(creator, SDO.name)
                        or graph.value(creator, SMA.name)
                    )
                if len(creator_name) > 0:
                    schema_metadata["creator"] = creator_name
            distribution = list(graph.objects(creative_work, SMA.distribution)) + list(
                graph.objects(creative_work, SDO.distribution)
            )
            schema_metadata["object_content_identifier"] = []
            for dist in distribution:
                durl = (
                    graph.value(dist, SMA.contentUrl)
                    or graph.value(dist, SMA.url)
                    or graph.value(dist, SDO.contentUrl)
                    or graph.value(dist, SDO.url)
                )
                dtype = graph.value(dist, SMA.encodingFormat) or graph.value(dist, SDO.encodingFormat)
                dsize = graph.value(dist, SMA.contentSize) or graph.value(dist, SDO.contentSize)
                if durl or dtype or dsize:
                    if idutils.is_url(str(durl)):
                        if dtype:
                            dtype = "/".join(str(dtype).split("/")[-2:])
                    schema_metadata["object_content_identifier"].append(
                        {"url": str(durl), "type": dtype, "size": str(dsize)}
                    )

            potential_action = list(graph.objects(creative_work, SMA.potentialAction)) + list(
                graph.objects(creative_work, SDO.potentialAction)
            )

            for potaction in potential_action:
                service_url, service_desc, service_type = None, None, None
                entry_point = graph.value(potaction, SMA.EntryPoint) or graph.value(potaction, SDO.EntryPoint)
                if not entry_point:
                    service_url = graph.value(potaction, SMA.target) or graph.value(potaction, SDO.target)

                else:
                    service_url = graph.value(entry_point, SMA.url) or graph.value(entry_point, SDO.url)
                    service_desc = graph.value(entry_point, SMA.urlTemplate) or graph.value(
                        entry_point, SDO.urlTemplate
                    )
                    service_type = graph.value(entry_point, SMA.additionalType) or graph.value(
                        entry_point, SDO.additionalType
                    )
                if service_url:
                    schema_metadata["object_content_identifier"].append(
                        {"url": service_url, "type": service_type, "service": service_desc}
                    )

            schema_metadata["measured_variable"] = []
            for variable in list(graph.objects(creative_work, SMA.variableMeasured)) + list(
                graph.objects(creative_work, SDO.variableMeasured)
            ):
                variablename = graph.value(variable, SMA.name) or graph.value(variable, SDO.name) or None

                if variablename:
                    schema_metadata["measured_variable"].append(variablename)
                else:
                    schema_metadata["measured_variable"].append(variable)

            # two routes to API services provided by repositories
            # 1) via the schema.org/DataCatalog 'offers' property
            # 2) via the schema.org/Project 'hasofferCatalog' property
            offer_catalog = graph.value(creative_work, SMA.hasOfferCatalog) or graph.value(
                creative_work, SDO.hasOfferCatalog
            )

            data_services = list(graph.objects(creative_work, SMA.offers)) + list(
                graph.objects(creative_work, SDO.offers)
            )

            if offer_catalog:
                data_services.extend(
                    list(graph.objects(offer_catalog, SMA.itemListElement))
                    + list(graph.objects(offer_catalog, SDO.itemListElement))
                )

            schema_metadata["metadata_service"] = []
            for data_service in data_services:
                if offer_catalog:
                    service_rdf_type = graph.value(data_service, RDF.type)
                    service_offer = data_service
                else:
                    service_offer = graph.value(data_service, SMA.itemOffered) or graph.value(
                        data_service, SDO.itemOffered
                    )
                    service_rdf_type = graph.value(service_offer, RDF.type)

                if "WebAPI" in str(service_rdf_type) or "Service" in str(service_rdf_type):
                    service_url = graph.value(service_offer, SMA.url) or graph.value(service_offer, SDO.url)
                    service_type = graph.value(service_offer, SMA.documentation) or graph.value(
                        service_offer, SDO.documentation
                    )
                    schema_metadata["metadata_service"].append({"url": str(service_url), "type": str(service_type)})
        return schema_metadata

    def get_dcat_metadata(self, graph):
        """Get the Data Catalog (DCAT) metadata given RDF graph.

        Parameters
        ----------
        graph : RDF.ConjunctiveGraph
            RDF Conjunctive Graph object

        Returns
        ------
        dict
            a dictionary of Ontology in RDF graph
        """
        dcat_metadata = dict()
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        CSVW = Namespace("http://www.w3.org/ns/csvw#")
        dcat_root_type = "Dataset"
        datasets = []
        cand_roots, object_types_dict = self.find_root_candidates(graph, ["Dataset", "Catalog"])
        print("CAND ROOTS DCAT: ", cand_roots, object_types_dict)
        if cand_roots:
            # prioritize Dataset type
            if "Dataset" not in cand_roots:
                dcat_root_type = next(iter(cand_roots))
        if dcat_root_type:
            datasets = list(graph[: RDF.type : DCAT[dcat_root_type]])
        table = list(graph[: RDF.type : CSVW.Column])
        # print("TABLE", len(table))
        if len(datasets) > 1:
            self.logger.info("FsF-F2-01M : Found more than one DCAT Dataset description, will use first one")
        if len(datasets) > 0:
            dcat_metadata = self.get_core_metadata(graph, datasets[0], type="Dataset")
            # distribution
            distribution = graph.objects(datasets[0], DCAT.distribution)
            # do something (check for table headers) with the table here..
            for t in table:
                print(t)
            dcat_metadata["object_content_identifier"] = []
            for dist in distribution:
                dtype, durl, dsize, dservice = None, None, None, None
                if not (
                    graph.value(dist, DCAT.accessURL)
                    or graph.value(dist, DCAT.downloadURL)
                    or graph.value(dist, DCAT.accessService)
                ):
                    self.logger.info(
                        "FsF-F2-01M : Trying to retrieve DCAT distributions from remote location -:" + str(dist)
                    )
                    try:
                        distgraph = rdflib.Graph()
                        disturl = str(dist)
                        distresponse = requests.get(disturl, headers={"Accept": "application/rdf+xml"})
                        if distresponse.text:
                            distgraph.parse(data=distresponse.text, format="application/rdf+xml")
                            extdist = list(distgraph[: RDF.type : DCAT.Distribution])
                            durl = distgraph.value(extdist[0], DCAT.accessURL) or distgraph.value(
                                extdist[0], DCAT.downloadURL
                            )
                            dsize = distgraph.value(extdist[0], DCAT.byteSize)
                            dtype = distgraph.value(extdist[0], DCAT.mediaType) or distgraph.value(
                                extdist[0], DC.format
                            )
                            self.logger.info(
                                "FsF-F2-01M : Found DCAT distribution URL info from remote location -:" + str(durl)
                            )
                    except Exception:
                        self.logger.info(
                            "FsF-F2-01M : Failed to retrieve DCAT distributions from remote location -:" + str(dist)
                        )
                        # print(e)
                        durl = str(dist)
                elif graph.value(dist, DCAT.accessService):
                    for dcat_service in graph.objects(dist, DCAT.accessService):
                        durl = graph.value(dcat_service, DCAT.endpointURL)
                        dtype = graph.value(dcat_service, DCTERMS.conformsTo)
                        dservice = graph.value(dcat_service, DCAT.endpointDescription)
                else:
                    durl = graph.value(dist, DCAT.accessURL) or graph.value(dist, DCAT.downloadURL)
                    # taking only one just to check if licence is available and not yet set
                    if not dcat_metadata.get("license"):
                        dcat_metadata["license"] = graph.value(dist, DCTERMS.license)
                    # TODO: check if this really works..
                    if not dcat_metadata.get("access_rights"):
                        dcat_metadata["access_rights"] = graph.value(dist, DCTERMS.accessRights) or graph.value(
                            dist, DCTERMS.rights
                        )
                    dtype = graph.value(dist, DCAT.mediaType)
                    dsize = graph.value(dist, DCAT.byteSize)
                if durl or dtype or dsize:
                    if idutils.is_url(str(durl)):
                        dtype = "/".join(str(dtype).split("/")[-2:])
                    dcat_metadata["object_content_identifier"].append(
                        {"url": str(durl), "type": dtype, "size": str(dsize), "service": str(dservice)}
                    )

            if dcat_metadata["object_content_identifier"]:
                self.logger.info(
                    "FsF-F3-01M : Found data links in DCAT.org metadata -: "
                    + str(dcat_metadata["object_content_identifier"])
                )
            # metadata services
            data_services = graph.objects(datasets[0], DCAT.service)
            dcat_metadata["metadata_service"] = []
            for data_service in data_services:
                service_url = graph.value(data_service, DCAT.endpointURL)
                service_type = graph.value(data_service, DCTERMS.conformsTo)
                dcat_metadata["metadata_service"].append({"url": str(service_url), "type": str(service_type)})
        return dcat_metadata

    def get_content_type(self):
        """Get the content type.

        Returns
        ------
        str
            a string of content type
        """
        return self.content_type
