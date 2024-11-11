# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import json
import re
import urllib

import dateutil
import idutils
import rdflib
import requests
from rdflib import RDFS, SKOS, Namespace
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

    def __init__(self, loggerinst, target_url=None, source=None, json_ld_content=None, pref_mime_type=None):
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
        self.main_entity_format = str(RDF)  # the main enties format e.g. dcat:Dataset => DCAT etc..
        self.metadata_format = MetadataFormats.RDF
        if self.source_name == MetadataSources.RDFA_EMBEDDED:
            self.metadata_format = MetadataFormats.RDFA
        self.json_ld_content = json_ld_content
        # self.rdf_graph = rdf_graph
        self.accept_type = AcceptTypes.rdf
        self.pref_mime_type = pref_mime_type

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
        print(type(graph))

        if isinstance(graph, rdflib.ConjunctiveGraph):
            for c in graph.contexts():
                print("CONTEXT: ", c)
        try:
            nm = graph.namespace_manager
            possible = set(graph.predicates()).union(graph.objects(None, RDF.type))
            alluris = set(graph.objects()).union(set(graph.subjects()))
            # namespaces from mentioned objects and subjects uris (best try)
            for uri in alluris:
                uri = str(uri)
                if idutils.is_url(uri):
                    for known_pattern in known_namespace_regex:
                        kpm = re.match(known_pattern, uri)
                        if kpm:
                            uri = kpm[0]
                            self.namespaces.append(str(uri))
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
            namespacedict = {}
            sortedns = {}
            for predicate in possible:
                prefix, namespace, local = nm.compute_qname(predicate)
                if namespace in namespacedict:
                    namespacedict[str(namespace)] += 1
                else:
                    namespacedict[str(namespace)] = 1
                namespaces[prefix] = namespace
            sortedns = sorted(namespacedict, key=lambda x: namespacedict[x], reverse=True)
            if sortedns:
                self.namespaces.extend(sortedns)
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
                    schema_metadata = self.get_schemaorg_metadata(rdf_response_graph)
                if bool(set(ontology_indicator) & set(graph_namespaces.values())):
                    self.logger.info("FsF-F2-01M : RDF Graph seems to contain SKOS/OWL metadata elements")
                    skos_metadata = self.get_ontology_metadata(rdf_response_graph)
                # merging metadata dicts
                try:
                    rdf_metadata = (
                        self.exclude_null(skos_metadata)
                        | self.exclude_null(dcat_metadata)
                        | self.exclude_null(schema_metadata)
                    )
                except:
                    print("RDF METADICT MERGE ERROR !")
                # else:
                if not rdf_metadata:
                    self.logger.info(
                        "FsF-F2-01M : Could not find DCAT, schema.org or SKOS/OWL metadata, continuing with generic SPARQL"
                    )
                    rdf_metadata = self.get_sparqled_metadata(rdf_response_graph)
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
            if self.pref_mime_type:
                requestHelper.addAcceptType(self.pref_mime_type)
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
            json_types = ["application/ld+json", "application/json", "application/vnd.schemaorg.ld+json"]
            if self.content_type in json_types or self.pref_mime_type in json_types:
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
                            "FsF-F2-01M : Try to parse JSON-LD retrieved as dict or list like structure from -: %s"
                            % (jsonld_source_url)
                        )
                        # JSON string from  dict delivered by extruct
                        try:
                            rdf_response = json.dumps(rdf_response)
                        except Exception as e:
                            print("RDF Collector Error (JSON DUMPS): ", e)
                            pass
                    # try to make graph from JSON-LD string
                    if isinstance(rdf_response, str) and rdf_response not in ["null", "None"]:
                        # url escape malformed (spaces) URIs
                        try:
                            suris = re.findall('"http[s]?:\/\/(.*?)"', rdf_response)
                            for suri in suris:
                                if " " in suri:
                                    rsuri = urllib.parse.quote(suri)
                                    rdf_response = rdf_response.replace(suri, rsuri)
                        except:
                            pass
                        # encoding
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
                            print("#####################################", type(rdf_response))
                            # pre-check for valid json
                            json_valid = False
                            try:
                                json_ = json.loads(rdf_response)
                                if isinstance(json_, dict):
                                    # add @context URIs to namespaces which are otherwise lost
                                    if isinstance(json_.get("@context"), list):
                                        self.namespaces.extend(json_.get("@context"))
                                    elif json_.get("@context"):
                                        self.namespaces.append(str(json_.get("@context")))
                                json_valid = True
                            except Exception:
                                self.logger.warning("FsF-F2-01M : Given JSON-LD seems to be invalid JSON")
                            if json_valid:
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
                + list(g.objects(item, SMA.keywords))
                + list(g.objects(item, SDO.keywords))
            ):
                meta["keywords"].append(str(keyword))
        # TODO creators, contributors
        if not meta.get("creator"):
            meta["creator"] = []
            for creator in (
                list(g.objects(item, DCTERMS.creator))
                + list(g.objects(item, DC.creator))
                + list(g.objects(item, SMA.creator))
                + list(g.objects(item, SDO.creator))
                + list(g.objects(item, SMA.author))
                + list(g.objects(item, SDO.author))
            ):
                if g.value(creator, FOAF.name):
                    meta["creator"].append(str(g.value(creator, FOAF.name)))
                elif g.value(creator, SMA.name):
                    meta["creator"].append(str(g.value(creator, SMA.name)))
                else:
                    meta["creator"].append(str(creator))

        if not meta.get("contributor"):
            meta["contributor"] = []
            for contributor in (
                list(g.objects(item, DCTERMS.contributor))
                + list(g.objects(item, DC.contributor))
                + list(g.objects(item, SMA.contributor))
                + list(g.objects(item, SDO.contributor))
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

    def get_main_entity(self, graph):
        main_entity_item, main_entity_type, main_entity_namespace = None, None, None
        # Finding the main entity of the graph
        graph_entity_list = []
        main_entity = {}
        creative_work_detected = False
        # we aim to only test creative works and subtypes taking the terms (names) from schema.org
        creative_work_types = Preprocessor.get_schema_org_creativeworks()
        try:
            for cw in list(graph.subjects(predicate=RDF.type)):
                types = list(graph.objects(predicate=RDF.type, subject=cw))
                types_names = []
                namespaces = []
                for tp in types:
                    type_name = re.split(r"/|#", str(tp))[-1]
                    if type_name.lower in creative_work_types:
                        creative_work_detected = True
                    types_names.append(type_name)
                    namespaces.append(tp)
                nsbj = len(list(graph.subjects(object=cw)))
                nprp = len(list(graph.objects(subject=cw)))
                graph_entity_list.append(
                    {"item": cw, "nosbj": nsbj, "noprp": nprp, "types": types_names, "ns": namespaces, "score": 0}
                )
            # score
            if graph_entity_list:
                max_prp = max(graph_entity_list, key=lambda x: x["noprp"])["noprp"]
                max_sbj = max(graph_entity_list, key=lambda x: x["nosbj"])["nosbj"]
                gk = 0
                for gel in graph_entity_list:
                    prp_score, sbj_score = 0, 0
                    if max_prp:
                        # better : more props
                        prp_score = 1 * gel["noprp"] / max_prp
                    if max_sbj:
                        # better : less props
                        sbj_score = 0.5 * (1 - gel["nosbj"] / max_sbj)
                    score = prp_score + sbj_score / 2
                    graph_entity_list[gk]["score"] = score
                    gk += 1
                main_entity = (sorted(graph_entity_list, key=lambda d: d["score"], reverse=True))[0]
                if not creative_work_detected:
                    self.logger.info(
                        "FsF-F2-01M : Detected main entity found in RDF graph seems not to be a creative work type"
                    )
                else:
                    self.logger.info("FsF-F2-01M : Detected main entity in RDF -: " + str(main_entity))
            main_entity_item, main_entity_type, main_entity_namespace = (
                main_entity.get("item"),
                main_entity.get("types"),
                main_entity.get("ns"),
            )
        except Exception as ee:
            self.logger.info(
                "FsF-F2-01M : Failed to detect main entity in metadata given as RDF Graph due to error -:" + str(ee)
            )
            print("MAIN ENTITY IDENTIFICATION ERROR: ", ee)
        return main_entity_item, main_entity_type, main_entity_namespace

    """def find_root_candidates(self, graph, allowed_types=["Dataset"]):
        allowed_types = [at.lower() for at in allowed_types if isinstance(at, str)]
        cand_creative_work = {}
        object_types_dict = {}
        graph_entity_list = []
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
                        # if type belongs to target URL there is no doubt this is the root
                        if str(creative_works[0]) == graph.identifier:
                            creative_work_subjects = []
                        # give Datasets always a try
                        if root_name.lower() == "dataset":
                            # but should have some props
                            if len(list(graph.objects(subject=creative_works[0]))) > 2:
                                creative_work_subjects = []
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

        return cand_creative_work, object_types_dict"""

    def get_schemaorg_metadata(self, graph):
        main_entity_id, main_entity_type, main_entity_namespace = self.get_main_entity(graph)
        creative_work_type = "Dataset"
        if main_entity_id:
            creative_work = main_entity_id
            creative_work_type = main_entity_type
        schema_metadata = {}
        SMA = Namespace("http://schema.org/")
        # use only schema.org properties and create graph using these.
        # is e.g. important in case schema.org is encoded as RDFa and variuos namespaces are used
        # this is tested by namepace elsewhere
        if "schema.org" in str(main_entity_namespace):
            self.main_entity_format = str(SDO)
            schema_metadata = self.get_core_metadata(graph, creative_work, type=creative_work_type)
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
            # distribution as hasPart which actually are MediaObjects
            for haspart in list(graph.objects(creative_work, SMA.hasPart)) + list(
                graph.objects(creative_work, SDO.hasPart)
            ):
                if "MediaObject" in str(graph.value(haspart, RDF.type)):
                    distribution.append(haspart)

            schema_metadata["object_content_identifier"] = []
            for dist in distribution:
                durl = (
                    graph.value(dist, SMA.contentUrl)
                    or graph.value(dist, SMA.url)
                    or graph.value(dist, SDO.contentUrl)
                    or graph.value(dist, SDO.url)
                )
                if not durl:
                    if isinstance(dist, rdflib.term.URIRef):
                        durl = str(dist)
                dtype = (
                    graph.value(dist, SMA.encodingFormat)
                    or graph.value(dist, SDO.encodingFormat)
                    or graph.value(dist, SMA.fileFormat)
                    or graph.value(dist, SDO.fileFormat)
                )
                dsize = (
                    graph.value(dist, SMA.contentSize)
                    or graph.value(dist, SDO.contentSize)
                    or graph.value(dist, SMA.fileSize)
                    or graph.value(dist, SDO.fileSize)
                )
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
            # temporalCoverage
            schema_metadata["coverage_temporal"] = []
            for temporal_info in list(graph.objects(creative_work, SMA.temporalCoverage)) + list(
                graph.objects(creative_work, SDO.temporalCoverage)
            ):
                temp_dates = []
                for temp_part in str(temporal_info).split(" "):
                    try:
                        temp_dates.append(str(dateutil.parser.parse(temp_part)))
                    except:
                        pass
                schema_metadata["coverage_temporal"].append({"dates": temp_dates, "name": str(temporal_info)})
            # spatialCoverage
            schema_metadata["coverage_spatial"] = []
            for spatial in (
                list(graph.objects(creative_work, SMA.spatialCoverage))
                + list(graph.objects(creative_work, SDO.spatialCoverage))
                + list(graph.objects(creative_work, SMA.spatial))
                + list(graph.objects(creative_work, SDO.spatial))
            ):
                spatial_info = {}
                if graph.value(spatial, SMA.name) or graph.value(spatial, SDO.name):
                    # Place name
                    spatial_info["name"] = graph.value(spatial, SMA.name) or graph.value(spatial, SDO.name)
                if graph.value(spatial, SMA.latitude) or graph.value(spatial, SDO.latitude):
                    spatial_info["coordinates"] = [
                        (graph.value(spatial, SMA.latitude) or graph.value(spatial, SDO.latitude)),
                        (graph.value(spatial, SMA.longitude) or graph.value(spatial, SDO.longitude)),
                    ]
                elif graph.value(spatial, SMA.geo) or graph.value(spatial, SDO.geo):
                    spatial_geo = graph.value(spatial, SMA.geo) or graph.value(spatial, SDO.geo)
                    if graph.value(spatial_geo, SMA.latitude) or graph.value(spatial_geo, SDO.longitude):
                        spatial_info["coordinates"] = [
                            (graph.value(spatial_geo, SMA.latitude) or graph.value(spatial_geo, SDO.latitude)),
                            (graph.value(spatial_geo, SMA.longitude) or graph.value(spatial_geo, SDO.longitude)),
                        ]
                    else:
                        spatial_extent = (
                            graph.value(spatial_geo, SMA.box)
                            or graph.value(spatial_geo, SDO.box)
                            or graph.value(spatial_geo, SMA.polygon)
                            or graph.value(spatial_geo, SDO.polygon)
                            or graph.value(spatial_geo, SMA.line)
                            or graph.value(spatial_geo, SDO.line)
                        )
                        spatial_info["coordinates"] = re.split(r"[\s,]+", str(spatial_extent))
                if spatial_info:
                    schema_metadata["coverage_spatial"].append(spatial_info)

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
        LOCN = Namespace("http://www.w3.org/ns/locn#")
        dcat_root_type = "Dataset"
        datasets = []
        main_entity_id, main_entity_type, main_entity_namespace = self.get_main_entity(graph)
        if main_entity_id:
            if dcat_root_type == "Catalog":
                self.logger.info(
                    "FsF-F2-01M : Main entity type seems to be a DCAT Catalog, checking for associated Datasets"
                )
                datasets = list(graph.objects(main_entity_id, DCAT.Dataset))
                if len(datasets) > 0:
                    self.logger.info(
                        "FsF-F2-01M : Found at least one DCAT Dataset enclosed in the DCAT Catalog, will take the first one for the analysis"
                    )
                    dcat_root_type = "Dataset"
            if not datasets:
                datasets = list(graph[: RDF.type : DCAT[dcat_root_type]])
        table = list(graph[: RDF.type : CSVW.Column])
        # print("TABLE", len(table))
        if len(datasets) > 1:
            self.logger.info("FsF-F2-01M : Found more than one DCAT Dataset description, will use first one")
        if len(datasets) > 0:
            self.main_entity_format = str(DCAT)
            dcat_metadata = self.get_core_metadata(graph, datasets[0], type=dcat_root_type)
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
                            dtype = (
                                distgraph.value(extdist[0], DCAT.mediaType)
                                or distgraph.value(extdist[0], DC.format)
                                or distgraph.value(extdist[0], DCTERMS.format)
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
                    dtype = (
                        graph.value(dist, DCAT.mediaType)
                        or graph.value(dist, DC.format)
                        or graph.value(dist, DCTERMS.format)
                    )
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
            # spatial coverage
            spatial_coverages = graph.objects(datasets[0], DCTERMS.spatial)
            dcat_metadata["coverage_spatial"] = []
            for spatial in spatial_coverages:
                spatial_name = graph.value(spatial, RDFS.label) or graph.value(spatial, SKOS.prefLabel)
                spatial_coordinate_data = (
                    graph.value(spatial, LOCN.geometry)
                    or graph.value(spatial, DCAT.bbox)
                    or graph.value(spatial, DCAT.centroid)
                )
                spatial_coordinates = spatial_coordinate_data
                # TODO: finalize parse_dcat_spatial and replace above with: spatial_coordinates = parse_dcat_spatial(spatial_coordinate_data)
                dcat_metadata["coverage_spatial"].append({"name": spatial_name, "coordinates": spatial_coordinates})
        return dcat_metadata

    def parse_dcat_spatial(self, spatial_text):
        """Parse the spatial info provided in DCAT e.g as WKT.

        Returns
        ------
        dict
            a dict containing coordinates, named places
        """

        return True

    def get_content_type(self):
        """Get the content type.

        Returns
        ------
        str
            a string of content type
        """
        return self.content_type
