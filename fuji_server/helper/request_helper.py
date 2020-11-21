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
import gzip
import json
import logging
import mimetypes
import re
import sys
import traceback
from enum import Enum
import extruct
import rdflib
import requests
import urllib
import ssl
from requests.packages.urllib3.exceptions import *
from tika import parser


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
        self.redirect_url = None
        self.accept_type = AcceptTypes.default.value
        self.http_response = None
        self.parse_response = None
        self.response_status = None
        self.response_content = None # normally the response body
        self.response_header = None

    def setAcceptType(self, accepttype):
        if not isinstance(accepttype, AcceptTypes):
            raise TypeError('type must be an instance of AcceptTypes enum')
        self.accept_type = accepttype.value

    def getAcceptType(self):
        return self.accept_type

    def setRequestUrl(self, url):
        self.request_url = url

    def getHTTPResponse(self):
        return self.http_response

    def getResponseContent(self):
        return self.response_content.decode('utf-8')

    def getParsedResponse(self):
        return self.parse_response

    def getResponseHeader(self):
        return self.response_header

    def content_negotiate(self, metric_id=''):
        #TODO: not necessarily to be done with the landing page e.g. http://purl.org/vocommons/voaf resolves to a version URL which responds HTML instead of RDF
        self.metric_id=metric_id
        source = 'html'
        status_code = None
        if self.request_url is not None:
            try:
                self.logger.info('{0} : Retrieving page {1}'.format(metric_id, self.request_url))
                #TODO: find another way to handle SSL certficate problems; e.g. perform the request twice and return at least a warning
                tp_request = urllib.request.Request(self.request_url, headers={'Accept': self.accept_type})
                context = ssl._create_unverified_context()
                tp_response =  urllib.request.urlopen(tp_request,context=context)
                self.http_response = tp_response

                self.response_content = tp_response.read()
                if tp_response.info().get('Content-Encoding') == 'gzip':
                    self.response_content = gzip.decompress(self.response_content)
                self.response_header = tp_response.getheaders()
                self.redirect_url = tp_response.geturl()
                #self.http_response = requests.get(self.request_url, headers={'Accept': self.accept_type})
                #status_code = self.http_response.status_code
                self.response_status = status_code = self.http_response.status
                self.logger.info(
                    '%s : Content negotiation accept=%s, status=%s ' % (metric_id, self.accept_type, str(status_code)))
                if status_code == 200:
                    content_type = self.http_response.headers.get("Content-Type")

                    if content_type is None:
                        content_type = mimetypes.guess_type(self.request_url, strict=True)[0]
                    if content_type is None:
                        #just in case tika is not running use this as quick check for the most obvious
                        if re.match(r"<!doctype html>|<html",str(self.response_content.decode('utf-8')).strip(),re.IGNORECASE) is not None:
                            content_type ='text/html'
                    if content_type is None:
                        parsedFile = parser.from_buffer(self.response_content)
                        content_type = parsedFile.get("metadata").get('Content-Type')

                    if content_type is not None:
                        if 'text/plain' in content_type:
                            source = 'text'
                            self.logger.info('%s : Plain text has been responded as content type!' % metric_id)
                            #try to find type by url
                            guessed_format = rdflib.util.guess_format(self.request_url)
                            if guessed_format is not None:
                                self.parse_response  = self.parse_rdf(self.response_content.decode('utf-8'), guessed_format)
                                source='rdf'
                                  #content_type = content_type.split(";", 1)[0]
                        else:
                            content_type = content_type.split(";", 1)[0]
                            while (True):
                                for at in AcceptTypes: #e.g., at.name = html, at.value = 'text/html, application/xhtml+xml'
                                    if content_type in at.value:
                                        if at.name == 'html':
                                            self.logger.info('%s : Found HTML page!' % metric_id)
                                            self.parse_response = self.parse_html(self.response_content.decode('utf-8'))
                                            source='html'
                                            break
                                        if at.name == 'xml': # TODO other types (xml)
                                            #in case the XML indeed is a RDF:
                                            # quick one:
                                            print(type(self.response_content))
                                            if self.response_content.decode('utf-8').find('<rdf:RDF') > -1:
                                                self.logger.info('%s : Found RDF document by tag!' % metric_id)
                                                self.parse_response = self.parse_rdf(self.response_content.decode('utf-8'), at.name)
                                                source='rdf'
                                            else:
                                                self.logger.info('%s : Found XML document!' % metric_id)
                                                self.parse_response  = self.response_content
                                                source='xml'
                                            break
                                        if at.name in ['schemaorg', 'json', 'jsonld', 'datacite_json']:
                                            self.parse_response  = json.loads(self.response_content)
                                            source='json'
                                            # result = json.loads(response.text)
                                            break
                                        if at.name in ['nt','rdf', 'rdfjson', 'ntriples', 'rdfxml', 'turtle']:
                                            self.parse_response  = self.parse_rdf(self.response_content, content_type)
                                            source='rdf'
                                            break

                                    # TODO (IMPORTANT) how to handle the rest e.g., text/plain, specify result type
                                break
                    else:
                        self.logger.warning('{0} : Content-type is NOT SPECIFIED'.format(metric_id))
                else:
                    self.logger.warning('{0} : NO successful response received, status code - {1}'.format(metric_id, str(status_code)))
            #except requests.exceptions.SSLError as e:
            except urllib.error.HTTPError as e:
            #    self.logger.warning('%s : SSL Error: Untrusted SSL certificate, failed to connect to %s ' % (metric_id, self.request_url))
            #    self.logger.exception("SSLError: {}".format(e))
            #    self.logger.exception('%s : SSL Error: Failed to connect to %s ' % (metric_id, self.request_url))
            #except requests.exceptions.RequestException as e:
                #All exceptions that Requests explicitly raises inherit from requests.exceptions.RequestException
                #self.logger.warning('%s : Request Error: Failed to connect to %s ' % (metric_id, self.request_url))
                self.logger.warning('%s : Content negotiation failed: accept=%s, status=%s ' % (metric_id, self.accept_type, str(e.code)))
                #self.logger.exception("{} : RequestException: {}".format(metric_id, e))
                #traceback.print_exc()
                #self.logger.exception('%s : Failed to connect to %s ' % (metric_id, self.request_url))
            except urllib.error.URLError as e:
                self.logger.warning("{} : RequestException: {} : {}".format(metric_id, e.reason, self.request_url))
                #self.logger.warning('%s : Content negotiation failed: accept=%s, status=%s ' % (metric_id, self.accept_type, str(e.code)))
        return source, self.parse_response

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
        self.logger.info('%s : Try to parse XML from %s' % (self.metric_id, self.request_url))

        print('Not yet implemented')
        return None
