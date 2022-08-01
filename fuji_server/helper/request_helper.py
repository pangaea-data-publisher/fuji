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
import gzip
import json
import logging
import mimetypes
import re
import sys
import traceback
from enum import Enum
import http.cookiejar

from io import BytesIO
from urllib.request import build_opener, HTTPCookieProcessor
from zipfile import ZipFile

import extruct
import lxml
import rdflib
import urllib
import ssl
from tika import parser

from fuji_server.helper.preprocessor import Preprocessor

class AcceptTypes(Enum):
    #TODO: this seems to be quite error prone..
    datacite_json = 'application/vnd.datacite.datacite+json'
    datacite_xml = 'application/vnd.datacite.datacite+xml'
    schemaorg = 'application/vnd.schemaorg.ld+json, application/ld+json'
    html = 'text/html, application/xhtml+xml'
    html_xml = 'text/html, application/xhtml+xml, application/xml;q=0.5, text/xml;q=0.5, application/rdf+xml;q=0.5'
    xml = 'application/xml, text/xml;q=0.5'
    json = 'application/json, text/json;q=0.5'
    jsonld = 'application/ld+json'
    atom = 'application/atom+xml'
    rdfjson = 'application/rdf+json'
    nt = 'text/n3, application/n-triples'
    rdfxml = 'application/rdf+xml, text/rdf;q=0.5, application/xml;q=0.1, text/xml;q=0.1'
    turtle = 'text/ttl, text/turtle, application/turtle, application/x-turtle;q=0.6, text/n3;q=0.3, text/rdf+n3;q=0.3, application/rdf+n3;q=0.3'
    rdf = 'text/turtle, application/turtle, application/x-turtle;q=0.8, application/rdf+xml, text/n3;q=0.9, text/rdf+n3;q=0.9,application/ld+json'
    default = '*/*'

    @staticmethod
    def list():
        atypes = []
        al = list(map(lambda c: c.value.split(','), AcceptTypes))
        return list(set([item.strip().split(';', 1)[0] for sublist in al for item in sublist]))


class RequestHelper:
    checked_content = {}
    def __init__(self, url, logInst: object = None):
        if logInst:
            self.logger = logInst
        else:
            self.logger = Preprocessor.logger  #logging.getLogger(__name__)
        self.request_url = url
        self.redirect_url = None
        self.accept_type = AcceptTypes.default.value
        self.http_response = None
        self.parse_response = None
        self.response_status = None
        self.response_content = None  # normally the response body
        self.response_header = None
        self.response_charset = 'utf-8'
        self.content_type = None
        self.content_size = 0
        #maximum size which will be downloaded and analysed by F-UJU
        self.max_content_size = Preprocessor.max_content_size
        self.checked_content_hash = None
    def setAcceptType(self, accepttype):
        if not isinstance(accepttype, AcceptTypes):
            raise TypeError('type must be an instance of AcceptTypes enum')
        self.accept_type = accepttype.value

    def addAcceptType(self, mime_type):
        self.accept_type= mime_type+','+self.accept_type

    def getAcceptType(self):
        return self.accept_type

    def setRequestUrl(self, url):
        self.request_url = url

    #def getHTTPResponse(self):
    #    return self.http_response

    def getResponseContent(self):
        return self.response_content

    def getParsedResponse(self):
        return self.parse_response

    def getResponseHeader(self):
        return dict(self.response_header)

    def content_decode(self, content):
        if isinstance(content, 'str'):
            a = 1
        return True

    def content_negotiate(self, metric_id='', ignore_html=True):
        #TODO: not necessarily to be done with the landing page e.g. http://purl.org/vocommons/voaf resolves to a version URL which responds HTML instead of RDF
        self.metric_id = metric_id
        source = 'html'
        status_code = None
        tp_response = None
        if self.request_url is not None:
            try:
                self.logger.info('{0} : Retrieving page -: {1} as {2}'.format(metric_id, self.request_url,
                                                                              self.accept_type))
                urllib.request.HTTPRedirectHandler.http_error_308 = urllib.request.HTTPRedirectHandler.http_error_301

                cookiejar =  http.cookiejar.MozillaCookieJar()
                context = ssl._create_unverified_context()
                context.set_ciphers('DEFAULT@SECLEVEL=1')

                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar), urllib.request.HTTPSHandler(context=context),urllib.request.HTTPHandler())

                urllib.request.install_opener(opener)

                tp_request = urllib.request.Request(self.request_url,
                                                    headers={
                                                        'Accept': self.accept_type,
                                                        'User-Agent': 'F-UJI'})
                try:
                    tp_response = opener.open(tp_request,timeout = 10)

                except urllib.error.URLError as e:
                    '''
                    if e.code >= 500:
                        if 'doi.org' in self.request_url:
                            self.logger.error(
                                '{0} : DataCite/DOI content negotiation failed, status code -: {1}, {2} - {3}'.format(
                                    metric_id, self.request_url, self.accept_type, str(e.code)))
                        else:
                            self.logger.error('{0} : Request failed, status code -: {1}, {2} - {3}'.format(
                                metric_id, self.request_url, self.accept_type, str(e.code)))
                    else:
                    '''
                    self.logger.warning('{0} : Request failed, reason -: {1}, {2} - {3}'.format(
                        metric_id, self.request_url, self.accept_type, str(e)))
                except urllib.error.HTTPError as e:
                    if e.code == 308:
                        self.logger.error(
                            '%s : F-UJI 308 redirect failed, most likely this patch: https://github.com/python/cpython/pull/19588/commits is not installed'
                            % metric_id)
                    elif e.code >= 500:
                        if 'doi.org' in self.request_url:
                            self.logger.error('{0} : DataCite/DOI content negotiation failed, status code -: {1}, {2} - {3}'.format(
                                    metric_id, self.request_url, self.accept_type, str(e.code)))
                        else:
                            self.logger.error('{0} : Request failed, status code -: {1}, {2} - {3}'.format(
                                metric_id, self.request_url, self.accept_type, str(e.code)))
                    else:
                        self.logger.warning('{0} : Request failed, status code -: {1}, {2} - {3}'.format(
                            metric_id, self.request_url, self.accept_type, str(e.code)))
                except Exception as e:
                    self.logger.warning('{0} : Request failed, reason -: {1}, {2} - {3}'.format(
                        metric_id, self.request_url, self.accept_type, str(e)))
                # redirect logger messages to metadata collection metric
                if metric_id == 'FsF-F1-02D':
                    self.logger.info('FsF-F2-01M : Trying to identify some EMBEDDED metadata in content retrieved during PID verification process (FsF-F1-02D)')
                    metric_id = 'FsF-F2-01M'

                if tp_response:
                    #self.http_response = tp_response
                    if tp_response.info().get('Content-Encoding') == 'gzip':
                        self.logger.info('FsF-F2-01M : Retrieving gzipped content')
                        self.response_content = gzip.decompress(self.response_content)
                    if tp_response.info().get('Content-Type') == 'application/zip':
                        self.logger.warning('FsF-F2-01M : Received zipped content which contains several files, therefore skipping tests')
                        self.response_content = None
                        source = 'zip'
                    if tp_response.info().get_content_charset():
                        self.response_charset = tp_response.info().get_content_charset()
                    self.response_header = tp_response.getheaders()
                    self.redirect_url = tp_response.geturl()
                    self.response_status = status_code = tp_response.status
                    self.logger.info('%s : Content negotiation accept=%s, status=%s ' %
                                     (metric_id, self.accept_type, str(status_code)))

                    self.content_type = self.getResponseHeader().get('Content-Type')
                    if not self.content_type:
                        self.content_type = self.getResponseHeader().get('content-type')
                    #print(self.accept_type,self.content_type)
                    # key for content cache
                    checked_content_id = hash(str(self.redirect_url ) + str(self.content_type))

                    if checked_content_id in self.checked_content:
                        self.checked_content_hash = checked_content_id
                        source = self.checked_content.get(checked_content_id).get('source')
                        self.parse_response = self.checked_content.get(checked_content_id).get('parse_response')
                        self.response_content = self.checked_content.get(checked_content_id).get('response_content')
                        self.content_type = self.checked_content.get(checked_content_id).get('content_type')
                        self.content_size = self.checked_content.get(checked_content_id).get('content_size')
                        content_truncated = self.checked_content.get(checked_content_id).get('content_truncated')
                        self.logger.info('%s : Using Cached response content' % metric_id)
                    else:
                        content_truncated = False
                        if status_code == 200:
                            try:
                                self.content_size = int(self.getResponseHeader().get('Content-Length'))
                                if not self.content_size:
                                    self.content_size = int(self.getResponseHeader().get('content-length'))
                            except Exception as e:
                                self.content_size = 0
                                pass

                            if source != 'zip':
                                if self.content_size > self.max_content_size:
                                    content_truncated = True
                                if sys.getsizeof(self.response_content) >= self.max_content_size or content_truncated:
                                    self.logger.warning('%s : Downloaded content has been TRUNCATED by F-UJI since it is larger than: -: %s' % (metric_id, str(self.max_content_size)))
                                self.response_content = tp_response.read(self.max_content_size)
                            if self.content_size == 0:
                                self.content_size = sys.getsizeof(self.response_content)
                            #try to find out if content type is byte then fix
                            if self.response_content:
                                try:
                                    self.response_content.decode('utf-8')
                                except (UnicodeDecodeError, AttributeError) as e:
                                    self.logger.warning('%s : Content UTF-8 encoding problem, trying to fix.. ' % metric_id)

                                    self.response_content = self.response_content.decode('utf-8', errors='replace')
                                    self.response_content = str(self.response_content).encode('utf-8')

                            #Now content should be utf-8 encoded
                            if content_truncated == True:
                                try:
                                    self.response_content =  self.response_content.rsplit(b'\n',1)[0]
                                except Exception as e:
                                    print('Error: '+str(e))
                            if self.content_type is None:
                                self.content_type = mimetypes.guess_type(self.request_url, strict=True)[0]
                            if self.content_type is None:
                                #just in case tika is not running use this as quick check for the most obvious
                                try:
                                    if re.search(b'<!doctype html>|<html',
                                                 self.response_content.strip(),
                                                 re.IGNORECASE) is not None:
                                        self.content_type = 'text/html'
                                except Exception as e:
                                    print(e)
                            if self.content_type is None:
                                parsedFile = parser.from_buffer(self.response_content)
                                self.content_type = parsedFile.get('metadata').get('Content-Type')
                            if 'application/xhtml+xml' in self.content_type:
                                try:
                                    if re.search(b'<!doctype html>|<html',
                                                 self.response_content.strip(),
                                                 re.IGNORECASE) is None:
                                        self.content_type = 'text/xml'
                                except Exception as e:
                                    print(e)


                            if self.content_type is not None:
                                if 'text/plain' in self.content_type:
                                    source = 'text'
                                    self.logger.info('%s : Plain text has been responded as content type! Trying to verify' % metric_id)
                                    #try to find type by url
                                    guessed_format = rdflib.util.guess_format(self.request_url)
                                    guess_format_type_dict = {'xml': 'application/xml', 'json-ld':'application/ld+json',
                                                              'turtle':'text/ttl','rdfa':'application/xhtml+xml',
                                                              'n3':'text/rdf+n3', 'nt':'application/n-triples',
                                                              'nquads':'application/n-quads','trix':'text/xml'
                                                              }
                                    if guessed_format is not None:
                                        if guessed_format in ['xml']:
                                            source ='xml'
                                            self.content_type = 'application/xml'
                                        elif guessed_format in guess_format_type_dict:
                                            source = 'rdf'
                                            self.content_type = guess_format_type_dict.get(guessed_format)
                                        else:
                                            source ='rdf'
                                            #not really the true mime types...
                                            self.content_type = 'application/rdf+'+str(guessed_format)
                                        self.logger.info(
                                            '%s : Expected plain text but identified different content type by file extension -: %s' % (metric_id, str(guessed_format)))


                                self.content_type = self.content_type.split(';', 1)[0]


                                while (True):
                                    for at in AcceptTypes:  #e.g., at.name = html, at.value = 'text/html, application/xhtml+xml'
                                        if at.name =='xml' and str(self.content_type).endswith('+xml'):
                                            self.content_type = 'text/xml'
                                        if self.content_type in at.value:
                                            if at.name == 'html':
                                                #since we already parse HTML in the landing page we ignore this and do not parse again
                                                if ignore_html == False:
                                                    self.logger.info('%s : Found HTML page!' % metric_id)
                                                    self.parse_response = self.parse_html(self.response_content)
                                                else:
                                                    self.logger.info('%s : Ignoring HTML response' % metric_id)
                                                    self.parse_response = None
                                                source = 'html'
                                                break
                                            if at.name == 'xml':  # TODO other types (xml)
                                                #in case the XML indeed is a RDF:
                                                root_element = ''
                                                try:
                                                    xmlparser = lxml.etree.XMLParser(strip_cdata=False,recover=True)
                                                    xmltree = lxml.etree.XML(self.response_content, xmlparser)
                                                    root_element = xmltree.tag
                                                    if content_truncated:
                                                        self.response_content = lxml.etree.tostring(xmltree)
                                                except Exception as e:
                                                    self.logger.warning('%s : Parsing XML document failed !' %
                                                                        metric_id)
                                                if re.match(r'(\{.+\})?RDF', root_element):
                                                    self.logger.info('%s : Expected XML but found RDF document by root tag!' % metric_id)
                                                    self.parse_response = self.response_content
                                                    #self.content_type ='application/xml+rdf'
                                                    source = 'rdf'
                                                else:
                                                    self.logger.info('%s : Found XML document!' % metric_id)
                                                    self.parse_response = self.response_content
                                                    source = 'xml'
                                                break
                                            if at.name in ['json', 'jsonld', 'datacite_json', 'schemaorg']:
                                                try:
                                                    self.parse_response = json.loads(self.response_content)
                                                    source = 'json'
                                                    # result = json.loads(response.text)
                                                    break
                                                except ValueError:
                                                    self.logger.info(
                                                        '{0} : Retrieved response seems not to be valid JSON'.format(
                                                            metric_id))

                                            if at.name in ['nt', 'rdf', 'rdfjson', 'ntriples', 'rdfxml', 'turtle','ttl','n3']:
                                                self.parse_response = self.response_content
                                                source = 'rdf'
                                                break
                                    break
                                # cache downloaded content
                                self.checked_content[checked_content_id] = {'source':source,
                                                                            'parse_response':self.parse_response,
                                                                            'response_content':self.response_content,
                                                                            'content_type':self.content_type,
                                                                            'content_size':self.content_size,
                                                                            'content_truncated':content_truncated}
                            else:
                                self.logger.warning('{0} : Content-type is NOT SPECIFIED'.format(metric_id))
                        else:
                            self.logger.warning('{0} : NO successful response received, status code -: {1}'.format(
                                metric_id, str(status_code)))
                    tp_response.close()
                else:

                    self.logger.warning('{0} : No response received from -: {1}'.format(metric_id, self.request_url))
            #except requests.exceptions.SSLError as e:
            except urllib.error.HTTPError as e:
                self.logger.warning('%s : Content negotiation failed -: accept=%s, status=%s ' %
                                    (metric_id, self.accept_type, str(e.code)))
                self.response_status = int(e.code)
            except urllib.error.URLError as e:
                self.logger.warning('{} : RequestException -: {} : {}'.format(metric_id, e.reason, self.request_url))
            except Exception as e:
                print(e)

                self.logger.warning('{} : Request Failed -: {} : {}'.format(metric_id, str(e), self.request_url))
        return source, self.parse_response

    def parse_html(self, html_texts):
        # extract contents from the landing page using extruct, which returns a dict with
        # keys 'json-ld', 'microdata', 'microformat','opengraph','rdfa'
        syntaxes = ['microdata', 'opengraph', 'json-ld']
        try:
            self.logger.info('%s : Trying to identify HTML embedded microdata or JSON -: %s' %
                                (self.metric_id, self.request_url))
            extracted = extruct.extract(html_texts, syntaxes=syntaxes)
        except Exception as e:
            extracted = None
            self.logger.warning('%s : Failed to parse HTML embedded microdata or JSON -: %s' %
                                (self.metric_id, self.request_url + ' ' + str(e)))
        if isinstance(extracted, dict):
            extracted = dict([(k, v) for k, v in extracted.items() if len(v) > 0])
            if len(extracted) == 0:
                extracted = None
        return extracted