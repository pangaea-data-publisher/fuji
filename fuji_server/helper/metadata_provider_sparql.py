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

from urllib.error import HTTPError

import rdflib
from SPARQLWrapper import SPARQLWrapper, SPARQLExceptions, RDFXML
from fuji_server.helper.metadata_provider import MetadataProvider

class SPARQLMetadataProvider(MetadataProvider):

    def getMetadata(self, queryString):
        wrapper = SPARQLWrapper(self.endpoint)
        wrapper.setQuery(queryString)
        wrapper.setReturnFormat(RDFXML)
        rdf_graph = None
        try:
            response = wrapper.query() #application/rdf+xml
            content_type = response.info()['content-type'].split(';')[0]
            if 'html' in content_type:
                self.logger.warning('{0} : Looks like not a valid SPARQL endpoint, content type -: {1} '.format(self.metric_id, content_type))
            else:
                rdf_graph = response.convert() #rdflib.graph.ConjunctiveGraph
                #print(rdf_graph.serialize(format='xml'))
                # https://www.w3.org/TR/sparql11-protocol/#query-success
                # The response body of a successful query operation with a 2XX response is either:
                # a SPARQL Results Document in XML, JSON, or CSV/TSV format (for SPARQL Query forms SELECT and ASK); or
                # an RDF graph [RDF-CONCEPTS] serialized, for example, in the RDF/XML syntax [RDF-XML], or an equivalent RDF graph serialization, for SPARQL Query forms DESCRIBE and CONSTRUCT
                if isinstance(rdf_graph, rdflib.graph.Graph) and len(rdf_graph) > 0 :
                    self.logger.info('{0} : number of triples found in the graph, format -: {1} of  {2}'.format(self.metric_id, len(rdf_graph), content_type))
                    for n in rdf_graph.namespaces():
                        self.namespaces.append(str(n[1]))
                else:
                    self.logger.warning('{0} : SPARQL query returns NO result.'.format(self.metric_id))
        except HTTPError as err1:
            self.logger.warning('{0} : HTTPError -: {1}'.format(self.metric_id, err1))
        except SPARQLExceptions.EndPointNotFound as err2:
            self.logger.warning('{0} : SPARQLExceptions -: {1}'.format(self.metric_id, err2))
        return rdf_graph, content_type

    def getNamespaces(self):
        return self.namespaces