import sys

import rdflib
from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from rdflib import Namespace
from rdflib.namespace import RDF
from rdflib.namespace import DCTERMS

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
        if isinstance(rdf_response,rdflib.graph.Graph):
            self.logger.info('FsF-F2-01M : Found RDF Graph')
            # TODO: set credit score for being valid RDF
            # TODO: since its valid RDF aka semantic representation, make sure FsF-I1-01M is passed and scored
            # TODO: check if graph is DCAT then..
            rdf_metadata=self.get_dcat_metadata(rdf_response)
        return self.source_name, rdf_metadata

    def get_dcat_metadata(self, graph):
        DCAT = Namespace("http://www.w3.org/ns/dcat#")
        datasets = list(graph[: RDF.type: DCAT.Dataset])
        dcat_metadata=dict()
        for dataset in datasets:
            #['creator', 'title', 'publisher', 'publication_date', 'summary', 'keywords','object_identifier']
            dcat_metadata['object_identifier']=dataset
            dcat_metadata['object_type']='Dataset'
            dcat_metadata['keywords']=[]
            dcat_metadata['title'] = graph.value(dataset, DCTERMS.title)
            dcat_metadata['summary']= graph.value(dataset, DCTERMS.description)
            dcat_metadata['publication_date'] = graph.value(dataset, DCTERMS.issued)
            dcat_metadata['publisher'] = graph.value(dataset, DCTERMS.publisher)
            for keyword in list(graph.objects(dataset, DCAT.keyword)):
                dcat_metadata['keywords'].append(str(keyword))
            distribution = graph.objects(dataset, DCAT.distribution)
            dcat_metadata['object_content_identifier']=[]
            for dist in distribution:
                durl=graph.value(dist, DCAT.accessURL)
                #taking only one just to check if licence is available
                dcat_metadata['license']=graph.value(dist, DCTERMS.license)
                # TODO: check if this really works..
                dcat_metadata['access_rights']=graph.value(dist, DCTERMS.accessRights)
                dtype=graph.value(dist, DCAT.mediaType)
                dsize=graph.value(dist, DCAT.bytesSize)
                dcat_metadata['object_content_identifier'].append({'url':durl,'type':dtype, 'size':dsize})
        return dcat_metadata
