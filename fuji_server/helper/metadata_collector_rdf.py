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
import json
import re
import sys

import idutils
import rdflib
import requests
from rdflib import Namespace, Graph
from rdflib.namespace import RDF
from rdflib.namespace import DCTERMS
from rdflib.namespace import DC
from rdflib.namespace import FOAF

from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from fuji_server.helper.metadata_mapper import Mapper


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

    def get_namespaces(self,graph):
        namespaces = {}
        try:
            nm = graph.namespace_manager
            possible = set(graph.predicates()).union(graph.objects(None, RDF.type))
            for predicate in possible:
                prefix, namespace, local = nm.compute_qname_strict(predicate)
                namespaces[prefix] = namespace
        except Exception as e:
            self.logger.info('FsF-F2-01M : RDF Namespace detection error -: {}'.format(e))
        return namespaces

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
            #print(self.target_url)
        requestHelper: RequestHelper = RequestHelper(self.target_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.rdf)
        neg_source, rdf_response = requestHelper.content_negotiate('FsF-F2-01M')
        #required for metric knowledge representation

        if requestHelper.getHTTPResponse() is not None:
            self.content_type = requestHelper.content_type
            if self.content_type is not None:
                self.content_type = self.content_type.split(';', 1)[0]

                #handle JSON-LD
                DCAT = Namespace('http://www.w3.org/ns/dcat#')
                if self.content_type == 'application/ld+json':
                    try:
                        self.logger.info('FsF-F2-01M : Try to parse RDF (JSON-LD) from -: %s' % (self.target_url))
                        jsonldgraph = rdflib.ConjunctiveGraph()
                        rdf_response_graph = jsonldgraph.parse(data=json.dumps(rdf_response), format='json-ld')
                        rdf_response_graph = jsonldgraph
                    except Exception as e:
                        self.logger.info('FsF-F2-01M : Parsing error, failed to extract JSON-LD -: {}'.format(e))
                else:
                    # parse RDF
                    parseformat = re.search(r'[\/+]([a-z]+)$', str(requestHelper.content_type))
                    if 'html' in str(parseformat[1]):
                        try:
                            self.logger.info('FsF-F2-01M : Try to parse RDF from -: %s' % (self.target_url))
                            graph = rdflib.Graph()
                            print(parseformat[1])
                            graph.parse(data=rdf_response, format=parseformat[1])
                            rdf_response_graph = graph
                        except:
                            error = sys.exc_info()[0]
                            self.logger.warning(
                                'FsF-F2-01M : Failed to parse RDF -: %s %s' % (self.target_url, str(error)))
                            self.logger.debug(error)
                    else:
                        self.logger.info('FsF-F2-01M : Seems to be HTML not RDF, therefore skipped parsing RDF from -: %s' % (self.target_url))

        #else:
        #    neg_source, rdf_response = 'html', self.rdf_graph

        ontology_indicator = [
            rdflib.term.URIRef('http://www.w3.org/2004/02/skos/core#'),
            rdflib.term.URIRef('http://www.w3.org/2002/07/owl#')
        ]
        if isinstance(rdf_response_graph, rdflib.graph.Graph):
            self.logger.info('FsF-F2-01M : Found RDF Graph which was sucessfully parsed')
            self.logger.info('FsF-F2-01M : Trying to identify namespaces in RDF Graph')
            graph_namespaces = self.get_namespaces(rdf_response_graph)
            #self.getNamespacesfromIRIs(graph_text)
            # TODO: set credit score for being valid RDF
            # TODO: since its valid RDF aka semantic representation, make sure FsF-I1-01M is passed and scored
            if rdflib.term.URIRef('http://www.w3.org/ns/dcat#') in graph_namespaces.values():
                self.logger.info('FsF-F2-01M : RDF Graph seems to contain DCAT metadata elements')
                rdf_metadata = self.get_dcat_metadata(rdf_response_graph)
            elif bool(set(ontology_indicator) & set(graph_namespaces.values())):
                rdf_metadata = self.get_ontology_metadata(rdf_response_graph)
            else:
                rdf_metadata = self.get_default_metadata(rdf_response_graph)
            #add found namespaces URIs to namespace
            for ns in graph_namespaces.values():
                self.namespaces.append(ns)
        else:
            self.logger.info('FsF-F2-01M : Expected RDF Graph but received -: {0}'.format(self.content_type))
        return self.source_name, rdf_metadata

    def get_default_metadata(self, g):
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
            if (len(g) > 1):
                self.logger.info('FsF-F2-01M : Trying to query generic SPARQL on RDF')
                r = g.query(Mapper.GENERIC_SPARQL.value)
                #this will only return the first result set (row)

                for row in sorted(r):
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
                self.logger.info(
                    'FsF-F2-01M : Graph seems to contain only one triple, skipping core metadata element test')
        except Exception as e:
            self.logger.info('FsF-F2-01M : SPARQLing error -: {}'.format(e))
        if len(meta) <= 0:
            if len(g) > 1:
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
        """Get the core metadata given RDF graph.

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
        meta = dict()
        #default sparql

        meta = self.get_default_metadata(g)
        meta['object_identifier'] = (g.value(item, DC.identifier) or g.value(item, DCTERMS.identifier))
        '''
        if self.source_name != self.getEnumSourceNames().RDFA.value:
            meta['object_identifier'] = str(item)
            meta['object_content_identifier'] = [{'url': str(item), 'type': 'application/rdf+xml'}]
        '''

        meta['title'] = (g.value(item, DC.title) or g.value(item, DCTERMS.title))
        meta['summary'] = (g.value(item, DC.description) or g.value(item, DCTERMS.description))
        meta['publication_date'] = (g.value(item, DC.date) or g.value(item, DCTERMS.date) or
                                    g.value(item, DCTERMS.issued))
        meta['publisher'] = (g.value(item, DC.publisher) or g.value(item, DCTERMS.publisher))
        meta['keywords'] = []
        for keyword in (list(g.objects(item, DCAT.keyword)) + list(g.objects(item, DCTERMS.subject)) +
                        list(g.objects(item, DC.subject))):
            meta['keywords'].append(str(keyword))
        #TODO creators, contributors
        meta['creator'] = g.value(item, DC.creator)
        meta['license'] = g.value(item, DCTERMS.license)
        meta['related_resources'] = []
        meta['access_level'] = (g.value(item, DCTERMS.accessRights) or g.value(item, DCTERMS.rights) or
                                g.value(item, DC.rights))
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

        # quick fix (avoid rdflib literal type exception)
        for v in [meta['title'], meta['summary'], meta['publisher']]:
            if v:
                v = v.toPython()
        if meta:
            meta['object_type'] = type

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
        if len(datasets) > 0:
            dcat_metadata = self.get_metadata(graph, datasets[0], type='Dataset')
            # publisher
            if idutils.is_url(dcat_metadata.get('publisher')) or dcat_metadata.get('publisher') is None:
                publisher = graph.value(datasets[0], DCTERMS.publisher)
                # FOAF preferred DCAT compliant
                publisher_name = graph.value(publisher, FOAF.name)
                dcat_metadata['publisher'] = publisher_name
                # in some cases a dc title is used (not exactly DCAT compliant)
                if dcat_metadata.get('publisher') is None:
                    publisher_title = graph.value(publisher, DCTERMS.title)
                    dcat_metadata['publisher'] = publisher_title

            # creator
            if idutils.is_url(dcat_metadata.get('creator')) or dcat_metadata.get('creator') is None:
                creators = graph.objects(datasets[0], DCTERMS.creator)
                creator_name = []
                for creator in creators:
                    creator_name.append(graph.value(creator, FOAF.name))
                if len(creator_name) > 0:
                    dcat_metadata['creator'] = creator_name

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
