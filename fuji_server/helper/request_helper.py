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
from fuji_server.helper.metadata_collector import MetadataFormats


class FUJIHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.redirect_list = []
        self.redirect_url = None
        self.redirect_status_list = []
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        self.redirect_url = newurl
        self.redirect_list.append(newurl)
        self.redirect_status_list.append((newurl,code))
        return super().redirect_request(req, fp, code, msg, hdrs, newurl)

class AcceptTypes(Enum):
    #TODO: this seems to be quite error prone..
    datacite_json = 'application/vnd.datacite.datacite+json'
    datacite_xml = 'application/vnd.datacite.datacite+xml'
    schemaorg = 'application/vnd.schemaorg.ld+json, application/ld+json'
    html = 'text/html, application/xhtml+xml'
    html_xml = 'text/html, application/xhtml+xml, application/xml;q=0.5, text/xml;q=0.5, application/rdf+xml;q=0.5'
    xml = 'application/xml, text/xml;q=0.5'
    #linkset = 'application/linkset+json, application/json, application/linkset'  <-- causes bug #329
    linkset = 'application/linkset+json, application/linkset'
    json = 'application/json, text/json;q=0.5'
    jsonld = 'application/ld+json'
    atom = 'application/atom+xml'
    rdfjson = 'application/rdf+json'
    nt = 'text/n3, application/n-triples'
    rdfxml = 'application/rdf+xml, text/rdf;q=0.5, application/xml;q=0.1, text/xml;q=0.1'
    turtle = 'text/ttl, text/turtle, application/turtle, application/x-turtle;q=0.6, text/n3;q=0.3, text/rdf+n3;q=0.3, application/rdf+n3;q=0.3'
    rdf = 'text/turtle, application/turtle, application/x-turtle;q=0.8, application/rdf+xml, text/n3;q=0.9, text/rdf+n3;q=0.9,application/ld+json'
    default = 'text/html, */*'

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
        self.format = None #Guessed Metadata Format
        self.request_url = url
        self.redirect_url = None
        self.resolved_url = None
        self.redirect_list = []
        self.redirect_status_list = []
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
        self.authtoken = None
        self.tokentype = None

    def setAuthToken(self,authtoken, tokentype):
        if isinstance(authtoken, str):
            self.authtoken = authtoken
        if tokentype in ['Bearer', 'Basic']:
            self.tokentype = tokentype

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
        self.metric_id = metric_id
        format = MetadataFormats.HTML
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
                redirect_handler = FUJIHTTPRedirectHandler()
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar), urllib.request.HTTPSHandler(context=context),urllib.request.HTTPHandler(),redirect_handler )
                urllib.request.install_opener(opener)
                request_headers = {
                    'Accept': self.accept_type,
                    'User-Agent': 'F-UJI'}
                if self.authtoken:
                    request_headers['Authorization'] = self.tokentype+' '+self.authtoken
                tp_request = urllib.request.Request(self.request_url,
                                                    headers=request_headers)
                try:
                    tp_response = opener.open(tp_request,timeout = 10)
                    self.redirect_list = redirect_handler.redirect_list
                    self.redirect_status_list = redirect_handler.redirect_status_list
                    self.redirect_url = redirect_handler.redirect_url
                except urllib.error.HTTPError as e:
                    self.response_status = int(e.code)
                    try:
                        self.redirect_url = redirect_handler.redirect_url
                        self.redirect_list = redirect_handler.redirect_list
                        self.redirect_status_list = redirect_handler.redirect_status_list
                    except:
                        pass
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
                    elif e.code == 400:
                        try:
                            #browsers automatically redirect to https in case a 400 occured for a http URL
                            if redirect_handler.redirect_list:
                                last_redirect_url = redirect_handler.redirect_list[-1]
                                if 'http://' in last_redirect_url:
                                    self.logger.warning(
                                        '{0} : HTTP 400 Error after redirect to http page , trying to redirect to https page for -: {1}'.format(
                                            metric_id, redirect_handler.redirect_list[-1]))
                                    # This is what Browsers sometimes do:
                                    last_redirect_url = last_redirect_url.replace('http:','https:')
                                    tp_request = urllib.request.Request(last_redirect_url,
                                                                        headers=request_headers)
                                    tp_response = opener.open(tp_request, timeout=10)
                        except Exception as e:
                            print('Redirect fix error:'+str(e))
                            pass
                    else:
                        self.logger.warning('{0} : Request failed, status code -: {1}, {2} - {3}'.format(
                            metric_id, self.request_url, self.accept_type, str(e.code)))
                except urllib.error.URLError as e:
                    self.logger.warning('{0} : Request failed, reason -: {1}, {2} - URLError: {3}'.format(
                        metric_id, self.request_url, self.accept_type, str(e)))
                    self.response_status = 900
                    try:
                        urlerrmatch = re.search(r'\[Errno\s+(\-?[0-9]+)', str(e))
                        # eg urlopen error [Errno 11001] getaddrinfo failed => DNS failed
                        if urlerrmatch:
                            print('Request URL Error: ', urlerrmatch[1])
                            self.response_status = int(urlerrmatch[1])
                    except:
                        pass

                    try:
                        self.redirect_url = redirect_handler.redirect_url
                        self.redirect_list = redirect_handler.redirect_list
                        self.redirect_status_list = redirect_handler.redirect_status_list
                    except:
                        pass
                except Exception as e:
                    print('Request ERROR: ', e)
                    self.logger.warning('{0} : Request failed, reason -: {1}, {2} - Error: {3}'.format(
                        metric_id, self.request_url, self.accept_type, str(e)))
                    # some internal status messages for optional analysis
                    try:
                        self.redirect_url = redirect_handler.redirect_url
                        self.redirect_list = redirect_handler.redirect_list
                        self.redirect_status_list = redirect_handler.redirect_status_list
                    except:
                        pass
                    if 'NewConnectionError' in str(e):
                        self.response_status = 601
                    elif 'RemoteDisconnected' in str(e):
                        self.response_status = 602
                    elif 'Read timed out' in str(e):
                        self.response_status = 603
                    elif 'ConnectionResetError' in str(e):
                        self.response_status = 604
                    else:
                        self.response_status = 1000
                # redirect logger messages to metadata collection metric
                if metric_id == 'FsF-F1-02D':
                    #self.logger.info('FsF-F2-01M : Trying to identify some EMBEDDED metadata in content retrieved during PID verification process (FsF-F1-02D)')
                    metric_id = 'FsF-F2-01M'

                if tp_response:
                    #self.http_response = tp_response
                    if tp_response.info().get('Content-Encoding') == 'gzip':
                        self.logger.info('FsF-F2-01M : Retrieving gzipped content')
                        self.response_content = gzip.decompress(self.response_content)
                    if tp_response.info().get('Content-Type') == 'application/zip':
                        self.logger.warning('FsF-F2-01M : Received zipped content which contains several files, therefore skipping tests')
                        self.response_content = None
                        format = None
                        #source = 'zip'
                    if tp_response.info().get_content_charset():
                        self.response_charset = tp_response.info().get_content_charset()
                    self.response_header = tp_response.getheaders()
                    self.redirect_url = tp_response.geturl()
                    self.response_status = status_code = tp_response.status
                    self.logger.info('%s : Content negotiation on %s accept=%s, status=%s ' %
                                     (metric_id, self.request_url, self.accept_type ,str(status_code)))
                    self.content_type = self.getResponseHeader().get('Content-Type')
                    if not self.content_type:
                        self.content_type = self.getResponseHeader().get('content-type')
                    #print(self.accept_type,self.content_type)
                    # key for content cache
                    checked_content_id = hash(str(self.redirect_url ) + str(self.content_type))

                    if checked_content_id in self.checked_content:
                        self.checked_content_hash = checked_content_id
                        format = self.checked_content.get(checked_content_id).get('format')
                        self.parse_response = self.checked_content.get(checked_content_id).get('parse_response')
                        self.response_content = self.checked_content.get(checked_content_id).get('response_content')
                        self.content_type = self.checked_content.get(checked_content_id).get('content_type')
                        self.content_size = self.checked_content.get(checked_content_id).get('content_size')
                        content_truncated = self.checked_content.get(checked_content_id).get('content_truncated')
                        self.logger.info('%s : Using Cached response content' % metric_id)
                    else:
                        self.logger.info('%s : Creating Cached response content' % metric_id)
                        content_truncated = False
                        if status_code == 200:
                            try:
                                self.content_size = int(self.getResponseHeader().get('Content-Length'))
                                if not self.content_size:
                                    self.content_size = int(self.getResponseHeader().get('content-length'))
                            except Exception as e:
                                self.content_size = 0
                                pass
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
                                    self.response_content = self.response_content.rsplit(b'\n',1)[0]
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
                                    print(e,'Request helper')
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
                                    print(e,'Request helper')
                            if self.content_type is not None:
                                if 'text/plain' in self.content_type:
                                    format = MetadataFormats.TEXT
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
                                            format = MetadataFormats.XML
                                            self.content_type = 'application/xml'
                                        elif guessed_format in guess_format_type_dict:
                                            format = MetadataFormats.RDF
                                            self.content_type = guess_format_type_dict.get(guessed_format)
                                        else:
                                            format =MetadataFormats.RDF
                                            #not really the true mime types...
                                            self.content_type = 'application/rdf+'+str(guessed_format)
                                        self.logger.info(
                                            '%s : Expected plain text but identified different content type by file extension -: %s' % (metric_id, str(guessed_format)))


                                self.content_type = self.content_type.split(';', 1)[0]
                                #init to avoid empty responses
                                self.parse_response = self.response_content
                                while (True):
                                    for at in AcceptTypes:  #e.g., at.name = html, at.value = 'text/html, application/xhtml+xml'
                                        if at.name =='xml' and str(self.content_type).endswith('+xml'):
                                            self.content_type = 'text/xml'

                                        if self.content_type in at.value:
                                            if at.name == 'html':
                                                #since we already parse HTML in the landing page we ignore this and do not parse again
                                                if ignore_html == False:
                                                    self.logger.info('%s : Found HTML page!' % metric_id)
                                                else:
                                                    self.logger.info('%s : Ignoring HTML response' % metric_id)
                                                    self.parse_response = None
                                                format = MetadataFormats.HTML
                                                break
                                            if at.name == 'xml' or str(self.content_type).endswith('+xml'):
                                                #in case the XML indeed is a RDF:
                                                root_element = ''
                                                try:
                                                    xmlparser = lxml.etree.XMLParser(strip_cdata=False,recover=True)
                                                    xmltree = lxml.etree.XML(self.response_content, xmlparser)
                                                    root_element = xmltree.tag
                                                    if content_truncated:
                                                        self.parse_response = self.response_content = lxml.etree.tostring(xmltree)
                                                except Exception as e:
                                                    self.logger.warning('%s : Parsing XML document failed !' %
                                                                        metric_id)
                                                if re.match(r'(\{.+\})?RDF', root_element):
                                                    self.logger.info('%s : Expected XML but found RDF document by root tag!' % metric_id)
                                                    format = MetadataFormats.RDF
                                                else:
                                                    self.logger.info('%s : Found XML document!' % metric_id)
                                                    format = MetadataFormats.XML
                                                break
                                            if at.name in ['json', 'jsonld', 'datacite_json', 'schemaorg'] or str(self.content_type).endswith('+json'):
                                                try:
                                                    self.parse_response = json.loads(self.response_content)
                                                    format = MetadataFormats.JSON
                                                    break
                                                except ValueError:
                                                    self.logger.info(
                                                        '{0} : Retrieved response seems not to be valid JSON'.format(
                                                            metric_id))

                                            if at.name in ['nt', 'rdf', 'rdfjson', 'ntriples', 'rdfxml', 'turtle','ttl','n3']:
                                                format = MetadataFormats.RDF
                                                break
                                            if at.name in ['linkset']:
                                                format = MetadataFormats.JSON
                                                break
                                    break
                                # cache downloaded content
                                self.checked_content[checked_content_id] = {'format':format,
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
                    self.logger.warning('{0} : No response received from -: {1}, {2}'.format(metric_id, self.request_url,self.accept_type))
            #except requests.exceptions.SSLError as e:
            except urllib.error.HTTPError as e:
                self.logger.warning('%s : Content negotiation failed -: accept=%s, status=%s ' %
                                    (metric_id, self.accept_type, str(e.code)))
                self.response_status = int(e.code)
            except urllib.error.URLError as e:
                self.logger.warning('{} : RequestException -: {} : {}'.format(metric_id, e.reason, self.request_url))
            except Exception as e:
                print(e, 'Request helper')
                self.logger.warning('{} : Request Failed -: {} : {}'.format(metric_id, str(e), self.request_url))
        return format, self.parse_response
