import sys

import rdflib
from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from rdflib import Namespace
from rdflib.namespace import RDF
from rdflib.namespace import DCTERMS
from rdflib.namespace import DC

from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes

class MetaDataCollectorSparql (MetaDataCollector):
    target_url=None
    def __init__(self,  loggerinst, target_url):
        self.target_url=target_url
        super().__init__(logger=loggerinst)

    def parse_metadata(self):
        self.source_name = self.getEnumSourceNames().LINKED_DATA.value
        self.logger.info('FsF-F2-01M : Extract metadata from {}'.format(self.source_name))
        rdf_metadata=dict()
        requestHelper: RequestHelper = RequestHelper(self.target_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.rdf)
        rdf_response = requestHelper.content_negotiate('FsF-F2-01M')
        ontology_indicator=[rdflib.term.URIRef('http://www.w3.org/2004/02/skos/core#'),rdflib.term.URIRef('http://www.w3.org/2002/07/owl#')]
        if isinstance(rdf_response,rdflib.graph.Graph):
            self.logger.info('FsF-F2-01M : Found RDF Graph')
            # TODO: set credit score for being valid RDF
            # TODO: since its valid RDF aka semantic representation, make sure FsF-I1-01M is passed and scored
            if rdflib.term.URIRef('http://www.w3.org/ns/dcat#') in dict(list(rdf_response.namespaces())).values():
                self.logger.info('FsF-F2-01M : RDF Graph seems to contain DCAT metadata elements')
                rdf_metadata = self.get_dcat_metadata(rdf_response)
            elif bool(set(ontology_indicator) & set(dict(list(rdf_response.namespaces())).values())):
                rdf_metadata = self.get_ontology_metadata(rdf_response)
        else:
            self.logger.info('FsF-F2-01M : Expected RDF Graph but received:'+str(type(rdf_response)))
        return self.source_name, rdf_metadata

    def get_namespaces(self):
        print('n')
        # TODO: complete get list of namespaces

    def get_metadata(self,g, item, type='Dataset'):
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        meta = dict()
        meta['object_identifier'] = str(item)
        meta['object_content_identifier'] = [{'url': str(item), 'type': 'application/rdf+xml'}]
        meta['object_type'] = type
        meta['title'] = (g.value(item, DC.title) or g.value(item, DCTERMS.title))
        meta['summary'] = (g.value(item, DC.description) or g.value(item, DCTERMS.description))
        meta['publication_date'] = (g.value(item, DC.date) or g.value(item, DCTERMS.date))
        meta['publisher'] = (g.value(item, DC.publisher) or g.value(item, DCTERMS.publisher))
        meta['keywords']=[]
        for keyword in (list(g.objects(item, DCAT.keyword)) + list(g.objects(item, DCTERMS.keyword)) + list(g.objects(item, DC.keyword))):
            meta['keywords'].append(str(keyword))
        #TODO creators, contributors
        meta['creator'] = g.value(item, DC.creator)
        meta['license'] = g.value(item, DCTERMS.license)
        return meta

    def get_ontology_metadata(self, graph):
        OWL=Namespace("http://www.w3.org/2002/07/owl#")
        SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
        ontologies=list(graph[: RDF.type: OWL.Ontology])
        if len(ontologies)>0:
            self.logger.info('FsF-F2-01M : RDF Graph seems to represent a OWL Ontology')
            ont_metadata=self.get_metadata(graph,ontologies[0],type='Ontology')
        else:
            ontologies = list(graph[: RDF.type: SKOS.Collection])
            if len(ontologies)>0:
                self.logger.info('FsF-F2-01M : RDF Graph seems to represent a SKOS Ontology')
                ont_metadata = self.get_metadata(graph, ontologies[0], type='Ontology')
            else:
                self.logger.info('FsF-F2-01M : Could not parse Ontology RDF')
        return ont_metadata

    def get_dcat_metadata(self, graph):
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        datasets = list(graph[: RDF.type: DCAT.Dataset])
        dcat_metadata = self.get_metadata(graph, datasets[0],type='Dataset')
        distribution = graph.objects(datasets[0], DCAT.distribution)
        dcat_metadata['object_content_identifier']=[]
        for dist in distribution:
            durl=graph.value(dist, DCAT.accessURL)
            #taking only one just to check if licence is available
            dcat_metadata['license']=graph.value(dist, DCTERMS.license)
            # TODO: check if this really works..
            dcat_metadata['access_rights']=graph.value(dist, DCTERMS.accessRights)
            dtype=graph.value(dist, DCAT.mediaType)
            dsize=graph.value(dist, DCAT.bytesSize)
            dcat_metadata['object_content_identifier'].append({'url':str(durl),'type':str(dtype), 'size':dsize})
            #TODO: add provenance metadata retrieval
        return dcat_metadata
