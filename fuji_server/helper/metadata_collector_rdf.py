# -*- coding: utf-8 -*-
# MIT License
#
# Copyright (c) 2020 PANGAEA (https://www.pangaea.de/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import json, rdflib_jsonld
import re
import sys

import extruct
import idutils
import rdflib
import requests
from rdflib import Namespace, Graph, URIRef, plugin
from rdflib.namespace import RDF
from rdflib.namespace import DCTERMS
from rdflib.namespace import DC
from rdflib.namespace import FOAF
from rdflib.namespace import SDO #schema.org

from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.metadata_collector_schemaorg import MetaDataCollectorSchemaOrg
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.preprocessor import Preprocessor
from pyld import jsonld

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

    def __init__(self, loggerinst, target_url, source):
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
        self.target_url = target_url
        self.content_type = None
        self.source_name = source
        #self.rdf_graph = rdf_graph
        super().__init__(logger=loggerinst)

    def getAllURIS(self, graph):
        founduris = []
        for link in list(graph.objects()):
            if isinstance(link, rdflib.term.URIRef):
                founduris.append(str(link))
        return founduris

    def set_namespaces(self,graph):
        namespaces = {}
        known_namespace_regex = [r'https?:\/\/vocab\.nerc\.ac\.uk\/collection\/[A-Z][0-9]+\/current\/',
                                 r'https?:\/\/purl\.obolibrary\.org\/obo\/[a-z]+(\.owl|#)']
        try:
            nm = graph.namespace_manager
            possible = set(graph.predicates()).union(graph.objects(None, RDF.type))
            alluris = set(graph.objects()).union(set(graph.subjects()))
            #namespaces from mentioned objects and subjects uris (best try)
            for uri in alluris:
                if idutils.is_url(uri):
                    for known_pattern in known_namespace_regex:
                        kpm = re.match(known_pattern, uri)
                        if kpm :
                            uri = kpm[0]
                            self.namespaces.append(uri)
                        else:
                            uri = str(uri).strip().rstrip('/#')
                            namespace_candidate = uri.rsplit('/', 1)[0]
                            if namespace_candidate != uri:
                                self.namespaces.append(namespace_candidate)
                            else:
                                namespace_candidate = uri.rsplit('#', 1)[0]
                                if namespace_candidate != uri:
                                    self.namespaces.append(namespace_candidate)
            #defined namespaces
            for predicate in possible:
                prefix, namespace, local = nm.compute_qname(predicate)
                namespaces[prefix] = namespace
                self.namespaces.append(str(namespace))
            self.namespaces = list(set(self.namespaces))

        except Exception as e:
            self.logger.info('FsF-F2-01M : RDF Namespace detection error -: {}'.format(e))
        return namespaces

    def get_metadata_from_graph(self, rdf_response_graph):
        rdf_metadata ={}
        if rdf_response_graph:
            ontology_indicator = [
                rdflib.term.URIRef('http://www.w3.org/2004/02/skos/core#'),
                rdflib.term.URIRef('http://www.w3.org/2002/07/owl#')
            ]
            if isinstance(rdf_response_graph, rdflib.graph.Graph) or isinstance(rdflib.graph.ConjunctiveGraph):
                self.logger.info('FsF-F2-01M : Found RDF Graph which was sucessfully parsed')
                self.logger.info('FsF-F2-01M : Trying to identify namespaces in RDF Graph')
                graph_namespaces = self.set_namespaces(rdf_response_graph)
                #self.getNamespacesfromIRIs(graph_text)
                # TODO: set credit score for being valid RDF
                # TODO: since its valid RDF aka semantic representation, make sure FsF-I1-01M is passed and scored
                if rdflib.term.URIRef('http://www.w3.org/ns/dcat#') in graph_namespaces.values():
                    self.logger.info('FsF-F2-01M : RDF Graph seems to contain DCAT metadata elements')
                    rdf_metadata = self.get_dcat_metadata(rdf_response_graph)
                elif rdflib.term.URIRef('http://schema.org/') in graph_namespaces.values():
                    self.logger.info('FsF-F2-01M : RDF Graph seems to contain schema.org metadata elements')
                    rdf_metadata = self.get_schemaorg_metadata(rdf_response_graph)
                elif bool(set(ontology_indicator) & set(graph_namespaces.values())):
                    self.logger.info('FsF-F2-01M : RDF Graph seems to contain SKOS/OWL metadata elements')
                    rdf_metadata = self.get_ontology_metadata(rdf_response_graph)
                #else:
                if not rdf_metadata:
                    self.logger.info('FsF-F2-01M : Could not find DCAT, schema.org or SKOS/OWL metadata, continuing with generic SPARQL')
                    #try to find root node
                    '''
                    typed_objects = list(rdf_response_graph.objects(predicate=RDF.type))
                    if typed_objects:
                        typed_nodes = list(rdf_response_graph[:RDF.type:typed_objects[0]])
                        if typed_nodes:
                            rdf_metadata = self.get_metadata(rdf_response_graph, typed_nodes[0], str(typed_objects[0]))
                    '''
                    #if not rdf_metadata or len(list(rdf_metadata)) <= 1:
                    rdf_metadata = self.get_sparqled_metadata(rdf_response_graph)

                #add found namespaces URIs to namespace
                #for ns in graph_namespaces.values():
                #    self.namespaces.append(ns)
            else:
                self.logger.info('FsF-F2-01M : Expected RDF Graph but received -: {0}'.format(self.content_type))
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
        #self.source_name = self.getEnumSourceNames().LINKED_DATA.value
        #self.logger.info('FsF-F2-01M : Trying to request RDF metadata from -: {}'.format(self.source_name))
        rdf_metadata = dict()
        rdf_response_graph = None
        #if self.rdf_graph is None:
        requestHelper: RequestHelper = RequestHelper(self.target_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.rdf)

        neg_source, rdf_response = requestHelper.content_negotiate('FsF-F2-01M')
        if requestHelper.checked_content_hash:
            if requestHelper.checked_content.get(requestHelper.checked_content_hash).get('checked') and 'xml' in requestHelper.content_type:
                requestHelper.response_content = None
                self.logger.info('FsF-F2-01M : Ignoring RDF since content already has been parsed as XML')

        #required for metric knowledge representation
        if requestHelper.response_content is not None:
            self.content_type = requestHelper.content_type
            if self.content_type is not None:
                self.content_type = self.content_type.split(';', 1)[0]
                #handle JSON-LD
                DCAT = Namespace('http://www.w3.org/ns/dcat#')
                if self.content_type in ['application/ld+json','application/json']:
                    self.logger.info('FsF-F2-01M : Try to parse RDF (JSON-LD) from -: %s' % (self.target_url))
                    if isinstance(rdf_response, dict):
                        try:
                            schemaorg_collector = MetaDataCollectorSchemaOrg(loggerinst=self.logger,
                                                                             sourcemetadata=[rdf_response],
                                                                             mapping=Mapper.SCHEMAORG_MAPPING,
                                                                             pidurl=None, source = MetaDataCollectorSchemaOrg.getEnumSourceNames().RDF_TYPED_LINKS.value)
                            source_schemaorg, rdf_metadata = schemaorg_collector.parse_metadata()
                            if rdf_metadata:
                                schemaorg_collector.setLinkedNamespaces(rdf_metadata)
                                self.namespaces = schemaorg_collector.namespaces
                                self.setLinkedNamespaces(str(rdf_response))
                            else:
                                rdf_response = json.dumps(rdf_response)
                            #wrong one given above
                        except Exception as e:
                            print('RDF Collector Error: ',e)
                            pass
                    #graph
                    if isinstance(rdf_response, str):
                        try:
                            jsonldgraph = rdflib.ConjunctiveGraph()
                            rdf_response_graph = jsonldgraph.parse(data=rdf_response, format='json-ld')
                            #rdf_response_graph = jsonldgraph
                            self.setLinkedNamespaces(self.getAllURIS(jsonldgraph))
                        except Exception as e:
                            print('JSON-LD parsing error', e)
                            self.logger.info('FsF-F2-01M : Parsing error, failed to extract JSON-LD -: {}'.format(e))
                else:
                    # parse RDF
                    parseformat = re.search(r'[\/+]([a-z0-9]+)$', str(requestHelper.content_type))
                    if parseformat:
                        if 'html' not in str(parseformat[1]) and 'zip' not in str(parseformat[1]) :
                            RDFparsed = False
                            self.logger.info('FsF-F2-01M : Try to parse RDF from -: %s as %s' % (self.target_url,parseformat[1]))
                            badline = None
                            while not RDFparsed:
                                try:
                                    graph = rdflib.Graph(identifier = self.target_url)
                                    graph.parse(data=rdf_response, format=parseformat[1])
                                    rdf_response_graph = graph
                                    self.setLinkedNamespaces(self.getAllURIS(rdf_response_graph))
                                    RDFparsed = True
                                except Exception as e:
                                    #<unknown>:74964:92: unclosed token
                                    errorlinematch = re.search(r'\sline\s([0-9]+)',str(e))
                                    if not errorlinematch:
                                        errorlinematch = re.search(r'<unknown>:([0-9]+)',str(e))
                                    if errorlinematch and parseformat[1] !='xml':
                                        if  int(errorlinematch[1])+1 != badline:
                                            badline = int(errorlinematch[1])
                                            self.logger.warning(
                                                'FsF-F2-01M : Failed to parse RDF, trying to fix and retry parsing everything before line -: %s ' % str(badline))
                                            splitRDF = rdf_response.splitlines()
                                            if len(splitRDF) >=1 and badline <= len(splitRDF) and badline > 1:
                                                rdf_response = b'\n'.join(splitRDF[:badline-1])
                                            else:
                                                RDFparsed = True # end reached
                                        else:
                                            RDFparsed = True
                                    else:
                                        RDFparsed = True # give up
                                    if not RDFparsed:
                                        continue
                                    else:
                                        self.logger.warning(
                                            'FsF-F2-01M : Failed to parse RDF -: %s %s' % (self.target_url, str(e)))
                        else:
                            self.logger.info('FsF-F2-01M : Seems to be HTML not RDF, therefore skipped parsing RDF from -: %s' % (self.target_url))
                    else:
                        self.logger.info('FsF-F2-01M : Could not determine RDF serialisation format for -: {}'.format(self.target_url))

        #else:
        #    neg_source, rdf_response = 'html', self.rdf_graph
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
            if (len(g) >= 1):
                self.logger.info('FsF-F2-01M : Trying to query generic SPARQL on RDF, found triples: -:'+str(len(g)))
                r = g.query(Mapper.GENERIC_SPARQL.value)
                for row in r:
                    for l, v in row.asdict().items():
                        if l is not None:
                            if l in [
                                    'references', 'source', 'isVersionOf', 'isReferencedBy', 'isPartOf', 'hasVersion',
                                    'replaces', 'hasPart', 'isReplacedBy', 'requires', 'isRequiredBy'
                            ]:
                                if not meta.get('related_resources'):
                                    meta['related_resources'] = []
                                meta['related_resources'].append({'related_resource': str(v), 'relation_type': l})
                            else:
                                meta[l] = str(v)
                    break
            else:
                self.logger.warning(
                    'FsF-F2-01M : Graph seems to contain no triple, skipping core metadata element test')
        except Exception as e:
            self.logger.info('FsF-F2-01M : SPARQLing error -: {}'.format(e))
        if len(meta) <= 0:
            goodtriples = []
            has_xhtml = False
            for t in list(g):
                # exclude xhtml properties/predicates:
                if not '/xhtml/vocab' in t[2]:
                    goodtriples.append(t)
                else:
                    has_xhtml = True
            if has_xhtml:
                self.logger.info('FsF-F2-01M : Found RDFa like triples but at least some of them seem to be XHTML properties which are excluded')
            if len(goodtriples) > 1:
                meta['object_type'] = 'Other'
                self.logger.info(
                    'FsF-F2-01M : Could not find core metadata elements through generic SPARQL query on RDF but found '
                    + str(len(g)) + ' triples in the given graph')
        else:
            self.logger.info('FsF-F2-01M : Found some core metadata elements through generic SPARQL query on RDF -: ' +
                             str(meta.keys()))
        return meta

    #TODO rename to: get_core_metadata
    def get_metadata(self, g, item, type='Dataset'):
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
        DCAT = Namespace('http://www.w3.org/ns/dcat#')
        SMA = Namespace('http://schema.org/')
        meta = dict()
        #default sparql
        #meta = self.get_default_metadata(g)
        self.logger.info('FsF-F2-01M : Trying to get some core domain agnostic (DCAT, DC, schema.org) metadata from RDF graph')
        if not meta.get('object_identifier'):
            meta['object_identifier'] = (g.value(item, DC.identifier) or
                                         g.value(item, DCTERMS.identifier) or
                                         g.value(item, SDO.identifier))
        '''
        if self.source_name != self.getEnumSourceNames().RDFA.value:
            meta['object_identifier'] = str(item)
            meta['object_content_identifier'] = [{'url': str(item), 'type': 'application/rdf+xml'}]
        '''

        if not meta.get('language'):
            meta['language'] = str(g.value(item, DC.language) or g.value(item, DCTERMS.language) or
                                   g.value(item, SDO.inLanguage) or g.value(item, SMA.inLanguage))
        if not meta.get('title'):
            meta['title'] = str(g.value(item, DC.title) or g.value(item, DCTERMS.title) or g.value(item, SMA.name) or g.value(item, SDO.name))
        if not meta.get('summary'):
            meta['summary'] = str(g.value(item, DC.description) or g.value(item, DCTERMS.description) or
                               g.value(item, SMA.description) or g.value(item, SDO.description)
                               or g.value(item, SMA.abstract) or g.value(item, SDO.abstract))
        if not meta.get('publication_date'):
            meta['publication_date'] = str(g.value(item, DC.date) or g.value(item, DCTERMS.date) or
                                        g.value(item, DCTERMS.issued)
                                        or  g.value(item, SMA.datePublished) or  g.value(item, SMA.dateCreated)
                                        or g.value(item, SDO.datePublished) or g.value(item, SDO.dateCreated)
                                        )
        if not meta.get('publisher'):
            meta['publisher']=[]
            for publisher in (list(g.objects(item, DC.publisher)) or list(g.objects(item, DCTERMS.publisher)) or
                                 list(g.objects(item, SMA.publisher)) or list(g.objects(item, SDO.publisher)) or
                                 list(g.objects(item, SMA.provider)) or list(g.objects(item, SDO.provider))):
                publishername = (g.value(publisher,FOAF.name) or (g.value(publisher,SMA.name))or (g.value(publisher,SDO.name)))
                if publishername:
                    meta['publisher'].append(str(publishername))
                else:
                    meta['publisher'].append(str(publisher))
            #meta['publisher'] = str(g.value(item, DC.publisher) or g.value(item, DCTERMS.publisher) or
            #                     g.value(item, SMA.publisher) or g.value(item, SDO.publisher) or g.value(item, SMA.provider) or g.value(item, SDO.provider))
        if not meta.get('keywords'):
            meta['keywords'] = []
            for keyword in (list(g.objects(item, DCAT.keyword)) + list(g.objects(item, DCTERMS.subject)) +
                            list(g.objects(item, DC.subject))
                            or list(g.objects(item, SMA.keywords)) or list(g.objects(item, SDO.keywords))):
                meta['keywords'].append(str(keyword))
        #TODO creators, contributors
        if not meta.get('creator'):
            meta['creator'] = []
            for creator in (list(g.objects(item, DCTERMS.creator)) or list(g.objects(item, DC.creator)) or list(g.objects(item, SMA.author))):
                if g.value(creator,FOAF.name):
                    meta['creator'].append(str(g.value(creator,FOAF.name)))
                else:
                    meta['creator'].append(str(creator))

        if not meta.get('contributor'):
            meta['contributor'] = []
            for contributor in (list(g.objects(item, DCTERMS.contributor)) or list(g.objects(item, DC.contributor)) or list(g.objects(item, SMA.contributor))):
                meta['contributor'].append(str(contributor))
        if not meta.get('license'):
            meta['license'] = str(g.value(item, DCTERMS.license) or g.value(item, SDO.license) or  g.value(item, SMA.license))
        if not meta.get('access_level'):
            meta['access_level'] = str(g.value(item, DCTERMS.accessRights) or g.value(item, DCTERMS.rights) or
                                    g.value(item, DC.rights)
                                    or g.value(item, SDO.conditionsOfAccess) or g.value(item, SMA.conditionsOfAccess) )
        if not meta.get('related_resources'):
            meta['related_resources'] = []
            for dctrelationtype in [
                    DCTERMS.references, DCTERMS.source, DCTERMS.isVersionOf, DCTERMS.isReferencedBy, DCTERMS.isPartOf,
                    DCTERMS.hasVersion, DCTERMS.replaces, DCTERMS.hasPart, DCTERMS.isReplacedBy, DCTERMS.requires,
                    DCTERMS.isRequiredBy
            ]:
                dctrelation = g.value(item, dctrelationtype)
                if dctrelation:
                    meta['related_resources'].append({
                        'related_resource': str(dctrelation),
                        'relation_type': str(dctrelationtype)
                    })
            for schemarelationtype in [
                SMA.isPartOf,  SMA.includedInDataCatalog, SMA.subjectOf, SMA.isBasedOn, SMA.sameAs,
                SDO.isPartOf, SDO.includedInDataCatalog, SDO.subjectOf, SDO.isBasedOn, SDO.sameAs
            ]:
                schemarelation = g.value(item, schemarelationtype)
                if schemarelation:
                    meta['related_resources'].append({
                        'related_resource': str(schemarelation),
                        'relation_type': str(schemarelationtype)
                    })

        if meta:
            meta['object_type'] = type
            meta = {k: v for k, v in meta.items() if v not in [None, 'None',[]]}
            self.logger.info(
                'FsF-F2-01M : Found some core domain agnostic (DCAT, DC, schema.org) metadata from RDF graph -: '+str(meta))
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
        OWL = Namespace('http://www.w3.org/2002/07/owl#')
        SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
        ontologies = list(graph[:RDF.type:OWL.Ontology])
        if len(ontologies) > 0:
            self.logger.info('FsF-F2-01M : RDF Graph seems to represent a OWL Ontology')
            ont_metadata = self.get_metadata(graph, ontologies[0], type='DefinedTermSet')
        else:
            ontologies = list(graph[:RDF.type:SKOS.ConceptScheme]) or list(graph[:RDF.type:SKOS.Collection])
            if len(ontologies) > 0:
                self.logger.info('FsF-F2-01M : RDF Graph seems to represent a SKOS Ontology')
                ont_metadata = self.get_metadata(graph, ontologies[0], type='DefinedTermSet')
            else:
                self.logger.info('FsF-F2-01M : Could not parse Ontology RDF')
        return ont_metadata

    def get_schemaorg_metadata(self, graph):
        #TODO: this is only some basic RDF/RDFa schema.org parsing... complete..
        #we will only test creative works and subtypes
        creative_work_types = Preprocessor.get_schema_org_creativeworks()
        creative_work = None
        schema_metadata={}
        SMA = Namespace('http://schema.org/')
        schema_org_nodes = []
        # use only schema.org properties and create graph using these.
        # is e.g. important in case schema.org is encoded as RDFa and variuos namespaces are used
        creative_work_type = 'Dataset'
        try:
            for root in rdflib.util.find_roots(graph, RDF.type):
                # we have https and http as allowed schema.org namespace protocols
                if 'schema.org' in str(root):
                    root_name = str(root).rsplit('/')[-1].strip()
                    if root_name.lower() in creative_work_types:
                        creative_works = list(graph[:RDF.type:root])
                        # Finding the schema.org root
                        if len(list(graph.subjects(object=creative_works[0]))) == 0:
                            creative_work = creative_works[0]
                            creative_work_type = root_name
                            break
        except Exception as e:
            self.logger.info('FsF-F2-01M : Schema.org RDF graph parsing failed -: '+str(e))
        if creative_work:
            schema_metadata = self.get_metadata(graph, creative_work, type = creative_work_type)
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
                    creator_name.append((graph.value(creator, SMA.familyName) or graph.value(creator, SDO.familyName)
                                         or graph.value(creator, SDO.name) or graph.value(creator, SMA.name) ))
                if len(creator_name) > 0:
                    schema_metadata['creator'] = creator_name

            distribution = (graph.objects(creative_works[0], SMA.distribution) or graph.objects(creative_works[0], SDO.distribution))
            schema_metadata['object_content_identifier'] = []
            for dist in distribution:
                durl = (graph.value(dist, SMA.contentUrl) or graph.value(dist, SDO.contentUrl))
                dtype = (graph.value(dist, SMA.encodingFormat) or graph.value(dist, SDO.encodingFormat))
                dsize = (graph.value(dist, SMA.contentSize) or graph.value(dist, SDO.contentSize))
                if durl or dtype or dsize:
                    if idutils.is_url(str(durl)):
                        dtype = '/'.join(str(dtype).split('/')[-2:])
                    schema_metadata['object_content_identifier'].append({
                        'url': str(durl),
                        'type': dtype,
                        'size': str(dsize)
                    })
            schema_metadata['measured_variable'] = []
            for variable  in (list(graph.objects(creative_works[0], SMA.variableMeasured))
                              or list(graph.objects(creative_works[0], SDO.variableMeasured))):
                variablename = (graph.value(variable, SMA.name) or graph.value(variable, SDO.name))
                if variablename:
                    schema_metadata['measured_variable'].append(variablename)
                else:
                    schema_metadata['measured_variable'].append(variable)

            #'measured_variable: variableMeasured[*].name || variableMeasured , object_size: size,' \

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
        DCAT = Namespace('http://www.w3.org/ns/dcat#')

        datasets = list(graph[:RDF.type:DCAT.Dataset])
        if len(datasets) > 1:
            self.logger.info('FsF-F2-01M : Found more than one DCAT Dataset description, will use first one')
        if len(datasets) > 0:
            dcat_metadata = self.get_metadata(graph, datasets[0], type='Dataset')
            # distribution
            distribution = graph.objects(datasets[0], DCAT.distribution)
            dcat_metadata['object_content_identifier'] = []
            for dist in distribution:
                dtype, durl, dsize = None, None, None
                if not (graph.value(dist, DCAT.accessURL) or graph.value(dist, DCAT.downloadURL)):
                    self.logger.info('FsF-F2-01M : Trying to retrieve DCAT distributions from remote location -:' +
                                     str(dist))
                    try:
                        distgraph = rdflib.Graph()
                        disturl = str(dist)
                        distresponse = requests.get(disturl, headers={'Accept': 'application/rdf+xml'})
                        if distresponse.text:
                            distgraph.parse(data=distresponse.text, format='application/rdf+xml')
                            extdist = list(distgraph[:RDF.type:DCAT.Distribution])
                            durl = (distgraph.value(extdist[0], DCAT.accessURL) or
                                    distgraph.value(extdist[0], DCAT.downloadURL))
                            dsize = distgraph.value(extdist[0], DCAT.byteSize)
                            dtype = distgraph.value(extdist[0], DCAT.mediaType)
                            self.logger.info('FsF-F2-01M : Found DCAT distribution URL info from remote location -:' +
                                             str(durl))
                    except Exception as e:
                        self.logger.info('FsF-F2-01M : Failed to retrieve DCAT distributions from remote location -:' +
                                         str(dist))
                        #print(e)
                        durl = str(dist)
                else:
                    durl = (graph.value(dist, DCAT.accessURL) or graph.value(dist, DCAT.downloadURL))
                    #taking only one just to check if licence is available
                    dcat_metadata['license'] = graph.value(dist, DCTERMS.license)
                    # TODO: check if this really works..
                    dcat_metadata['access_rights'] = (graph.value(dist, DCTERMS.accessRights) or
                                                      graph.value(dist, DCTERMS.rights))
                    dtype = graph.value(dist, DCAT.mediaType)
                    dsize = graph.value(dist, DCAT.bytesSize)
                if durl or dtype or dsize:
                    if idutils.is_url(str(durl)):
                        dtype = '/'.join(str(dtype).split('/')[-2:])
                    dcat_metadata['object_content_identifier'].append({
                        'url': str(durl),
                        'type': dtype,
                        'size': str(dsize)
                    })

            if dcat_metadata['object_content_identifier']:
                self.logger.info('FsF-F3-01M : Found data links in DCAT.org metadata -: ' +
                                 str(dcat_metadata['object_content_identifier']))
                #TODO: add provenance metadata retrieval
        #else:
        #    self.logger.info('FsF-F2-01M : Found DCAT content but could not correctly parse metadata')
            #in order to keep DCAT in the found metadata list, we need to pass at least one metadata value..
            #dcat_metadata['object_type'] = 'Dataset'
        return dcat_metadata
        #rdf_meta.query(self.metadata_mapping.value)
        #print(rdf_meta)
        #return None

    def get_content_type(self):
        """Get the content type.

        Returns
        ------
        str
            a string of content type
        """
        return self.content_type
