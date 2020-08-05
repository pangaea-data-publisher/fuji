import logging
import sys
from enum import Enum
import extruct
import rdflib
import requests
from requests.packages.urllib3.exceptions import *
from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer

class AcceptTypes(Enum):
    #TODO: this seems to be quite error prone..
    datacite_json = 'application/vnd.datacite.datacite+json'
    datacite_xml = 'application/vnd.datacite.datacite+xml'
    schemaorg = 'application/vnd.schemaorg.ld+json'
    html = 'text/html, application/xhtml+xml'
    xml = 'application/xml, text/xml;q=0.5'
    json = 'application/json, text/json;q=0.5'
    jsonld = 'application/ld+json'
    rdfjson = 'application/rdf+json'
    nt = 'text/n3, application/n-triples'
    rdfxml = 'application/rdf+xml, text/rdf;q=0.5, application/xml;q=0.1, text/xml;q=0.1'
    turtle = 'text/ttl, text/turtle, application/turtle, application/x-turtle;q=0.6, text/n3;q=0.3, text/rdf+n3;q=0.3, application/rdf+n3;q=0.3'
    rdf = 'text/turtle, application/turtle, application/x-turtle;q=0.8, application/rdf+xml, text/n3;q=0.9, text/rdf+n3;q=0.9'
    default = '*/*'

class RequestHelper:
    def __init__(self, url, logInst: object = None):
        if logInst:
            self.logger = logInst
        else :
            self.logger = logging.getLogger(self.__class__.__name__)
        self.request_url = url
        self.accept_type = AcceptTypes.default.value
        self.http_response = None
        self.parse_response = None

    def setAcceptType(self, accept_type):
        if not isinstance(accept_type, AcceptTypes):
            raise TypeError('type must be an instance of AcceptTypes enum')
        self.accept_type = accept_type.value

    def setRequestUrl(self, url):
        self.request_url = url

    def getHTTPResponse(self):
        return self.http_response

    def getParsedResponse(self):
        return self.parse_response

    def content_negotiate(self, metric_id=''):
        #TODO: not necessarily to be done with the landing page e.g. http://purl.org/vocommons/voaf resolves to a version URL which responds HTML instead of RDF
        self.metric_id=metric_id
        if self.request_url is not None:
            try:
                self.logger.info('{0} : Retrieving page {1}'.format(metric_id, self.request_url))
                self.http_response = requests.get(self.request_url, headers={'Accept': self.accept_type},verify=True)
                status_code = self.http_response.status_code
                self.logger.info(
                    '%s : Content negotiation accept=%s, status=%s ' % (metric_id, self.accept_type, str(status_code)))
                if status_code == 200:
                    content_type = self.http_response.headers["Content-Type"]
                    #TODO content type is sometimes wrongly given.. try to infer the type from request
                    if content_type is not None:
                        if 'text/plain' in content_type:
                            self.logger.info('%s : Plain text has been responded as content type!' % metric_id)
                            #try to find type by url
                            guessed_format = rdflib.util.guess_format(self.request_url)
                            if guessed_format is not None:
                                self.parse_response  = self.parse_rdf(self.http_response.text, guessed_format)
                                  #content_type = content_type.split(";", 1)[0]
                        else:
                            content_type = content_type.split(";", 1)[0]
                            while (True):
                                for at in AcceptTypes: #e.g., at.name = html, at.value = 'text/html, application/xhtml+xml'
                                    if content_type in at.value:
                                        if at.name == 'html':
                                            self.logger.info('%s : Found HTML page!' % metric_id)
                                            self.parse_response  = self.parse_html(self.http_response.text)
                                            break
                                        if at.name == 'xml': # TODO other types (xml)

                                            #in case the XML indeed is a RDF:
                                            # quick one:
                                            if self.http_response.text.find('<rdf:RDF') > -1:
                                                self.logger.info('%s : Found RDF document by tag!' % metric_id)
                                                self.parse_response = self.parse_rdf(self.http_response.text, at.name)
                                            else:
                                                self.logger.info('%s : Found XML document!' % metric_id)
                                                self.parse_response  = self.http_response
                                            break
                                        if at.name in ['schemaorg', 'json', 'jsonld', 'datacite_json']:
                                            self.parse_response  = self.http_response.json()
                                            # result = json.loads(response.text)
                                            break
                                        if at.name in ['nt','rdf', 'rdfjson', 'ntriples', 'rdfxml', 'turtle']:
                                            self.parse_response  = self.parse_rdf(self.http_response.text, content_type)
                                            break

                                    # TODO (IMPORTANT) how to handle the rest e.g., text/plain, specify result type
                                break
               # else:
                #    self.logger.warning('{} : NO successful response received', format(metric_id))
            except requests.exceptions.SSLError as e:
                self.logger.warning('%s : SSL Error: Failed to connect to %s ' % (metric_id, self.request_url))
                self.logger.exception("SSLError: {}".format(e))
                self.logger.exception('%s : SSL Error: Failed to connect to %s ' % (metric_id, self.request_url))
            except requests.exceptions.RequestException as e:
                self.logger.warning('%s : Request Error: Failed to connect to %s ' % (metric_id, self.request_url))
                self.logger.exception("RequestException: {}".format(e))
                self.logger.exception('%s : Failed to connect to %s ' % (metric_id, self.request_url))
        return self.parse_response

    def parse_html(self, html_texts):
        # extract contents from the landing page using extruct, which returns a dict with
        # keys 'json-ld', 'microdata', 'microformat','opengraph','rdfa'
        try:
            extracted = extruct.extract(html_texts.encode('utf8'))
        except:
            extracted=None
            self.logger.warning('%s : Failed to perform parsing on microdata or JSON %s' % (self.metric_id, self.request_url))
        #filtered = {k: v for k, v in extracted.items() if v}
        return extracted

    def parse_rdf(self, response, type):
        # TODO (not complete!!)
        # https://rdflib.readthedocs.io/en/stable/plugin_parsers.html
        # https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#rdflib.graph.Graph.parse
        graph = None
        try:
            self.logger.info('%s : Try to parse RDF from %s' % (self.metric_id, self.request_url))
            graph = rdflib.Graph()
            graph.parse(data=response, format=type)
            #queries have to be done in specific metadata collector classes
        except:
            error = sys.exc_info()[0]
            self.logger.warning('%s : Failed to parse RDF %s %s' % (self.metric_id, self.request_url, str(error)))
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

    def parse_xml(self, response, type):
        # TODO: implement a generic XML parsing which checks domain specific
        # document schema and performs a XSLT to get metadata elements
        # write some domain specific XSLTs and/or parsers
        print('Not yet implemented')
