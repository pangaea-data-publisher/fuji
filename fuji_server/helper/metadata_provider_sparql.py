# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from urllib.error import HTTPError

import rdflib
from SPARQLWrapper import RDFXML, SPARQLExceptions, SPARQLWrapper

from fuji_server.helper.metadata_provider import MetadataProvider


class SPARQLMetadataProvider(MetadataProvider):
    """A metadata provider class to get the metadata from a SPARQL query

    ...

    Methods
    -------
    getMetadataStandards()
        Method will return the metadata standards in the namespaces
    getMetadata(queryString)
        Method that will return RDF graph and content type given the SPARQL query
    getNamespaces()
        Method to get namespaces

    """

    def getMetadataStandards(self):
        """Method will return the matadata standards in the namespaces

        Returns
        -------
        dict
            A dictionary of metadata standards.

        """

        standards = {v: k for v, k in enumerate(self.namespaces)}
        return standards

    def getMetadata(self, queryString):
        """Method will return RDF graph and namespace given the SPARQL query

        Returns
        -------
        rdflib.ConjunctiveGraph
            RDF graph from the result of SPARQL query
        str
            Content type of the result of SPARQL query
        """

        wrapper = SPARQLWrapper(self.endpoint)
        wrapper.setQuery(queryString)
        wrapper.setReturnFormat(RDFXML)

        rdf_graph = None
        content_type = None
        try:
            response = wrapper.query()  # application/rdf+xml
            content_type = response.info()["content-type"].split(";")[0]
            if "html" in content_type:
                self.logger.warning(
                    f"{self.metric_id} : Looks like not a valid SPARQL endpoint, content type -: {content_type} "
                )
            else:
                rdf_graph = response.convert()  # rdflib.graph.ConjunctiveGraph
                # print(rdf_graph.serialize(format='xml'))
                # https://www.w3.org/TR/sparql11-protocol/#query-success
                # The response body of a successful query operation with a 2XX response is either:
                # a SPARQL Results Document in XML, JSON, or CSV/TSV format (for SPARQL Query forms SELECT and ASK); or
                # an RDF graph [RDF-CONCEPTS] serialized, for example, in the RDF/XML syntax [RDF-XML], or an equivalent RDF graph serialization, for SPARQL Query forms DESCRIBE and CONSTRUCT
                if isinstance(rdf_graph, rdflib.graph.Graph) and len(rdf_graph) > 0:
                    self.logger.info(
                        "{} : number of triples found in the graph, format -: {} of  {}".format(
                            self.metric_id, len(rdf_graph), content_type
                        )
                    )
                    graph_text = rdf_graph.serialize(format="ttl")

                    for n in rdf_graph.namespaces():
                        self.namespaces.append(str(n[1]))
                    self.getNamespacesfromIRIs(graph_text)
                else:
                    self.logger.warning(f"{self.metric_id} : SPARQL query returns NO result.")
        except HTTPError as err1:
            self.logger.warning(f"{self.metric_id} : HTTPError -: {err1}")
        except SPARQLExceptions.EndPointNotFound as err2:
            self.logger.warning(f"{self.metric_id} : SPARQLExceptions -: {err2}")
        return rdf_graph, content_type

    def getNamespaces(self):
        return self.namespaces
