import logging
from typing import Any, Union

import extruct
import rdflib
import requests
from enum import Enum


class AcceptTypes(Enum):
    datacite_json = 'application/vnd.datacite.datacite+json'
    datacite_xml = 'application/vnd.datacite.datacite+xml'
    schemaorg = 'application/vnd.schemaorg.ld+json',
    html = 'text/html, application/xhtml+xml'
    json = 'application/json, text/json;q=0.5'
    jsonld = 'application/ld+json'
    rdfjson = 'application/rdf+json'
    ntriples = 'text/plain,application/n-triples'
    rdfxml = 'application/rdf+xml, text/rdf;q=0.5, application/xml;q=0.1, text/xml;q=0.1'
    turtle = 'text/turtle, application/turtle, application/x-turtle;q=0.6, text/n3;q=0.3, text/rdf+n3;q=0.3, application/rdf+n3;q=0.3'
    rdf = 'text/turtle, application/turtle, application/x-turtle;q=0.8, application/rdf+xml, text/n3;q=0.9, text/rdf+n3;q=0.9, application/xhtml+xml;q=0.5, */*;q=0.1'
    default = '*/*'

class RequestHelper:
    def __init__(self, pidurl=None, logger_inst=None):
        if logger_inst:
            self.logger = logger_inst
        else:
            self.logger = logging.getLogger(self.__class__.__name__)
        self.pid_url = pidurl
        self.accept_type = AcceptTypes.html.value

    def setAcceptType(self, type):
        if not isinstance(type, AcceptTypes):
            raise TypeError('type must be an instance of AcceptTypes enum')
        self.accept_type = type.value

    def content_negotiate(self, metric_id):
        result = None
        result_type = 'html'
        if self.pid_url is not None:
            try:
                response = requests.get(self.pid_url, headers={'Accept': self.accept_type})
                self.logger.info(metric_id + ': Content negotiation accept=%s, status=%s ' % (
                    self.accept_type, str(response.status_code)))
                if response.status_code == 200:
                    content_type = response.headers["Content-Type"]
                    if content_type is not None:
                        content_type = content_type.split(";", 1)[0]
                        for at in AcceptTypes: #e.g., at.name = html, at.value = 'text/html, application/xhtml+xml'
                            if content_type in at.value:
                                if at.name == 'html':  # TODO other types (xml)
                                    result = self.parse_html(response.text)
                                elif at.name in {'schemaorg', 'json', 'jsonld', 'datacite_json'}:
                                    result = response.json()
                                    # result = json.loads(response.text)
                                    result_type = 'json'
                                elif at.name in {'rdf', 'jsonld', 'rdfjson', 'ntriples', 'rdfxml', 'turtle'}:
                                    result = self.parse_rdf(response.text, content_type)
                                    result_type = 'rdf'
                                else:
                                    result = self.parse_html(
                                        response.text)  # TODO (IMPORTANT) how to handle the rest e.g., text/plain, specify result type
                                break
            except requests.exceptions.RequestException as e:
                self.logger.exception("RequestException: {}".format(e))
                self.logger.exception("%s: , RequestException, accept = %s" % (self.metric_id, self.AcceptTypes))
        return result, result_type

    def parse_html(self, html_texts):
        # extract contents from the landing page using extruct, which returns a dict with
        # keys 'json-ld', 'microdata', 'microformat','opengraph','rdfa'
        extracted = extruct.extract(html_texts.encode('utf8'))
        filtered = {k: v for k, v in extracted.items() if v}
        return filtered

    def parse_rdf(self, response, mime_type):  # TODO (not complete!!)
        # https://rdflib.readthedocs.io/en/stable/plugin_parsers.html
        # https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#rdflib.graph.Graph.parse
        graph = None
        try:
            graph = rdflib.Graph()
            graph.parse(data=response, format=mime_type)
            # rdf:Description rdf:about=...
            predicate_query = graph.query("""
                                 select ?sub ?predicates ?obj
                                 where {?sub ?predicates ?obj}
                                 """)
            # for s, p, o in predicate_query:
            # print(s, p, o)
        except rdflib.exceptions.Error as error:
            self.logger.debug(error)
        return graph

    # RDF data syntaxes (xml, n3, ntriples, trix, JSON-LD, ...)
    # Turtle is a simplified, RDF-only subset of N3.
    # N-Quads media type is application/n-quads and encoding is UTF-8.
    # N3 (Notation3) media type is text/n3, but text/rdf+n3 is also accepted. Character encoding is UTF-8.
    # JSON-LD media type is application/ld+json and the encoding is UTF-8.
    # RDF/JSON media type is application/rdf+json and the encoding is UTF-8.
    # RDF/XML media type is application/rdf+xml, but application/xml and text/xml are also accepted. The character encoding is UTF-8.
    # N-Triples media type is application/n-triples and encoding is in UTF-8.
    # Turtle media type is text/turtle, but application/x-turtle is also accepted. Character encoding is UTF-8.
    # RDFa media type is application/xhtml+xml and the encoding is UTF-8.
    # TODO handle 406 Not Acceptable or 300 Multiple Choices
    # TODO transform accept_types and parser types into a class
