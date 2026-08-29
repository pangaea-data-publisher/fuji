# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT
import asyncio
import gzip
import http.cookiejar
import json
import mimetypes
import re
import ssl
import traceback
import urllib
from enum import Enum
from http.client import IncompleteRead

import lxml
import rdflib
from is_antibot import is_antibot
from tika import parser

from fuji_server.helper.browser_manager import BrowserManager
from fuji_server.helper.metadata_collector import MetadataFormats
from fuji_server.helper.preprocessor import Preprocessor


class FUJIHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.redirect_list = []
        self.redirect_url = None
        self.redirect_status_list = []
        self.status_list = []

    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        self.redirect_url = newurl
        self.redirect_list.append(newurl)
        self.redirect_status_list.append((newurl, code))
        self.status_list.append(code)
        return super().redirect_request(req, fp, code, msg, hdrs, newurl)


class AcceptTypes(Enum):
    # TODO: this seems to be quite error prone..
    datacite_json = "application/vnd.datacite.datacite+json"
    datacite_xml = "application/vnd.datacite.datacite+xml"
    schemaorg = "application/vnd.schemaorg.ld+json, application/ld+json"
    html = "text/html, application/xhtml+xml"
    html_xml = "text/html, application/xhtml+xml, application/xml;q=0.5, text/xml;q=0.5, application/rdf+xml;q=0.5"
    xml = "application/xml, text/xml;q=0.5"
    # linkset = 'application/linkset+json, application/json, application/linkset'  <-- causes bug #329
    linkset = "application/linkset, application/linkset+json"
    json = "application/json, text/json;q=0.5"
    jsonld = "application/ld+json"
    atom = "application/atom+xml"
    rdfjson = "application/rdf+json"
    nt = "text/n3, application/n-triples"
    rdfxml = "application/rdf+xml, text/rdf;q=0.5, application/xml;q=0.1, text/xml;q=0.1"
    turtle = "text/ttl, text/turtle, application/turtle, application/x-turtle;q=0.6, text/n3;q=0.3, text/rdf+n3;q=0.3, application/rdf+n3;q=0.3"
    rdf = "text/turtle, application/turtle, application/x-turtle;q=0.8, application/rdf+xml, text/n3;q=0.9, text/rdf+n3;q=0.9,application/ld+json"
    default = "text/html, */*"

    @staticmethod
    def list():
        al = list(map(lambda c: c.value.split(","), AcceptTypes))
        return list(set([item.strip().split(";", 1)[0] for sublist in al for item in sublist]))


class ResponseData:
    def __init__(self):
        self.status = 0
        self.headers = {}
        self.content = None
        self.url = None
        self.truncated = False
        self.content_type = None
        self.content_size = 0
        self.content_length = 0
        self.charset = None
        self.content_encoding = None
        self.redirect_url = None
        self.redirect_list = []
        self.redirect_status_list = []
        self.status_list = []
        self.parsed_content = None
        self.parse_format = None

    def getHeader(self):
        return dict(self.headers or {})

    def getContent(self):
        return self.content

    def getParsedResponse(self):
        return self.parsed_content


class RequestHelper:
    checked_content = {}

    rdf_type_dict = {
        "xml": "application/xml",
        "json-ld": "application/ld+json",
        "turtle": "text/ttl",
        "rdfa": "application/xhtml+xml",
        "n3": "text/rdf+n3",
        "nt": "application/n-triples",
        "nquads": "application/n-quads",
        "trix": "text/xml",
    }

    def __init__(self, url, logInst: object = None):
        self.user_agent = "F-UJI/4.0 (+https://github.com/pangaea-data-publisher/fuji)"
        self.browser_like_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; F-UJI)"
        self.logger = logInst if logInst else Preprocessor.logger
        self.response = ResponseData()
        self.request_url = url.split("#")[0]
        self.redirect_url = None
        self.redirect_list = []
        self.accept_type = AcceptTypes.default.value
        # maximum size which will be downloaded and analysed by F-UJU
        self.max_content_size = Preprocessor.max_content_size
        self.checked_content_hash = None
        self.authtoken = None
        self.tokentype = None
        # print('REQUEST HELPER CACHE: ', len(self.checked_content))

    @classmethod
    def reset_cache(cls):
        cls.checked_content = {}

    def setAuthToken(self, authtoken, tokentype):
        if isinstance(authtoken, str):
            self.authtoken = authtoken
        if tokentype in ["Bearer", "Basic"]:
            self.tokentype = tokentype

    def setAcceptType(self, accepttype):
        if not isinstance(accepttype, AcceptTypes):
            raise TypeError("type must be an instance of AcceptTypes enum")
        self.accept_type = accepttype.value

    def addAcceptType(self, mime_type):
        self.accept_type = mime_type + "," + self.accept_type

    def getAcceptType(self):
        return self.accept_type

    def setRequestUrl(self, url):
        self.request_url = url

    """def content_decode(self, content):
        if isinstance(content, "str"):
            pass
        return True"""

    async def request_content(self, metric_id="", ignore_html=True, check_antibot=False):
        return await asyncio.to_thread(self._request_content_sync, metric_id, ignore_html, check_antibot)

    def _check_antibot(self, metric_id):
        try:
            body = self.response.content
            if isinstance(body, bytes):
                body = body.decode("utf-8", errors="replace")
            antibot_result = is_antibot(
                headers=self.response.getHeader(),
                body=body,
                status_code=self.response.status,
            )
            if antibot_result.detected:
                self.logger.error(
                    metric_id
                    + " : ANTIBOT PROTECTION detected. You need to expose SOME metadata to allow FAIR assessment -: "
                    + str(antibot_result.detection)
                    + ", "
                    + str(antibot_result.provider)
                )
        except Exception as e:
            print("antibot detection failed...", e)

    def _set_response_object(self, response, redirect_handler=None):
        try:
            self.response.content = response.read(self.max_content_size + 1)
        except IncompleteRead as e:
            content = e.partial
            self.logger.warning(
                "%s : Could not create response object, incomplete HTTP response: received %d bytes",
                self.metric_id,
                len(content),
            )

        self.response.headers = response.headers
        self.response.redirect_url = response.url
        self.response.content_type = self.response.headers.get("Content-Type")

        self.response.content_length = response.headers.get("Content-Length")
        self.response.content_size = 0
        self.response.truncated = False

        self.response.status = getattr(response, "status", getattr(response, "code", None))
        if redirect_handler is not None:
            if redirect_handler.redirect_list:
                self.response.redirect_url = redirect_handler.redirect_url
                self.response.redirect_list = redirect_handler.redirect_list
                self.response.redirect_status_list = redirect_handler.redirect_status_list
                self.response.status_list = redirect_handler.status_list

        if self.response.content:
            try:
                self.response.content.decode("utf-8")
            except (UnicodeDecodeError, AttributeError):
                self.logger.warning("%s : Content UTF-8 encoding problem, trying to fix.. " % self.metric_id)
                self.response.content = self.response.content.decode("utf-8", errors="replace").encode("utf-8")
            self.response.content_size = len(self.response.content)
            if self.response.content_size > self.max_content_size:
                self.response.truncated = True

            if self.response.truncated is True and self.response.content_size > 0:
                try:
                    self.response.content = self.response.content.rsplit(b"\n", 1)[0]
                except Exception as e:
                    print("Error: " + str(e))

            self.response.content_type = self._detect_mime_type()
            self.response.parse_format, self.response.parsed_content = self._set_format_and_parsed_content()

    def _request_content_sync(self, metric_id="", ignore_html=True, check_antibot=False):

        # async def request_content(self, metric_id="", ignore_html=True):
        self.metric_id = metric_id
        tp_response = None
        if self.request_url is not None:
            try:
                self.logger.info(f"{metric_id} : Retrieving page -: {self.request_url} as {self.accept_type}")
                urllib.request.HTTPRedirectHandler.http_error_308 = urllib.request.HTTPRedirectHandler.http_error_301

                cookiejar = http.cookiejar.MozillaCookieJar()
                context = ssl._create_unverified_context()
                context.set_ciphers("DEFAULT@SECLEVEL=0")
                redirect_handler = FUJIHTTPRedirectHandler()
                opener = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(cookiejar),
                    urllib.request.HTTPSHandler(context=context),
                    urllib.request.HTTPHandler(),
                    redirect_handler,
                )
                urllib.request.install_opener(opener)
                request_headers = {"Accept": self.accept_type, "User-Agent": self.user_agent}
                # print('HEADERS: ',request_headers)
                if self.authtoken:
                    request_headers["Authorization"] = self.tokentype + " " + self.authtoken
                tp_request = urllib.request.Request(self.request_url, headers=request_headers)
                try:
                    tp_response = opener.open(tp_request, timeout=10)
                    self._set_response_object(tp_response, redirect_handler)
                except urllib.error.HTTPError as e:
                    self._set_response_object(e, redirect_handler)
                    if e.code == 308:
                        self.logger.error(
                            "%s : F-UJI 308 redirect failed, most likely this patch: https://github.com/python/cpython/pull/19588/commits is not installed"
                            % metric_id
                        )
                    elif e.code == 405 or e.code == 403:
                        self.logger.error(
                            "%s : Received a 405 or 403 HTTP error, either a 'method not allowed' error or the host denied the User-Agent used (web scraping detection), retrying..."
                            % metric_id
                        )
                    elif e.code >= 500:
                        if "doi.org" in self.request_url:
                            self.logger.error(
                                "{} : DataCite/DOI content negotiation failed, status code -: {}, {} - {}".format(
                                    metric_id, self.request_url, self.accept_type, str(e.code)
                                )
                            )
                        else:
                            self.logger.error(
                                "{} : Request failed (status code >=500), status code -: {}, {} - {}".format(
                                    metric_id, self.request_url, self.accept_type, str(e.code)
                                )
                            )
                    elif e.code == 400:
                        self.logger.warning(
                            "{} : Request failed, server did not understand it, status code -: {}, {} - {}".format(
                                metric_id, self.request_url, self.accept_type, str(e.code)
                            )
                        )
                        if "html" in self.accept_type:
                            try:
                                # browsers automatically redirect to https in case a 400 occured for a http URL
                                if redirect_handler.redirect_list:
                                    last_redirect_url = redirect_handler.redirect_list[-1]
                                    if "http://" in last_redirect_url:
                                        self.logger.warning(
                                            "{} : HTTP 400 Error after redirect to http page , trying to redirect to https page for -: {}".format(
                                                metric_id, redirect_handler.redirect_list[-1]
                                            )
                                        )
                                        # This is what Browsers sometimes do:
                                        last_redirect_url = last_redirect_url.replace("http:", "https:")
                                        tp_request = urllib.request.Request(last_redirect_url, headers=request_headers)
                                        tp_response = opener.open(tp_request, timeout=10)
                                        self._set_response_object(tp_response, redirect_handler)
                            except Exception as e:
                                print("Redirect fix error:" + str(e))
                                pass
                    elif e.code == 410:
                        self.logger.warning(
                            "{} : Content GONE, this could be a tombstone page, status code -: {}, {} - {}".format(
                                metric_id, self.request_url, self.accept_type, str(e.code)
                            )
                        )
                        try:
                            tp_response = e  # so take the error response as response instead
                            self._set_response_object(tp_response)
                        except Exception as e:
                            print("ERROR ", e)
                    else:
                        self.logger.warning(
                            "{} : Request failed, status code -: {}, {} - {}".format(
                                metric_id, self.request_url, self.accept_type, str(e.code)
                            )
                        )
                except urllib.error.URLError as e:
                    self.logger.warning(
                        "{} : Request failed, reason -: {}, {} - URLError: {}".format(
                            metric_id, self.request_url, self.accept_type, str(e)
                        )
                    )
                    self.response.status = 900
                    if hasattr(e.reason, "errno"):
                        self.response.status = e.reason.errno
                    if redirect_handler:
                        self.response.redirect_url = getattr(redirect_handler, "redirect_url", None)
                        self.response.redirect_list = getattr(redirect_handler, "redirect_list", [])
                        self.response.redirect_status_list = getattr(redirect_handler, "redirect_status_list", [])
                        self.response.status_list = getattr(redirect_handler, "status_list", [])
                except Exception as e:
                    traceback.print_exc()
                    print("Request ERROR: ", e)
                    self.logger.warning(
                        "{} : Request failed, reason -: {}, {} - Error: {}".format(
                            metric_id, self.request_url, self.accept_type, str(e)
                        )
                    )
                    # some internal status messages for optional analysis
                    try:
                        self.response.redirect_url = redirect_handler.redirect_url
                        self.response.redirect_list = redirect_handler.redirect_list
                        self.response.redirect_status_list = redirect_handler.redirect_status_list
                        self.response.status_list = redirect_handler.status_list
                    except:
                        pass
                    if "NewConnectionError" in str(e):
                        self.response.status = 601
                    elif "RemoteDisconnected" in str(e):
                        self.response.status = 602
                    elif "Read timed out" in str(e):
                        self.response.status = 603
                    elif "ConnectionResetError" in str(e):
                        self.response.status = 604
                    else:
                        self.response.status = 1000
                # redirect logger messages to metadata collection metric
                if metric_id == "FsF-F1-02D":
                    metric_id = "FsF-F2-01M"
            # except requests.exceptions.SSLError as e:
            except urllib.error.HTTPError as e:
                self.logger.warning(
                    f"{metric_id} : Content negotiation failed -: accept={self.accept_type}, status={e.code!s} "
                )
                self.response.status = int(e.code)
            except urllib.error.URLError as e:
                self.logger.warning(f"{metric_id} : RequestException -: {e.reason} : {self.request_url}")
            except Exception as e:
                self.logger.warning(f"{metric_id} : Request Failed -: {e!s} : {self.request_url}")

            # check if anti-robot software is in place
            if check_antibot:
                self._check_antibot(metric_id)

    async def render_page(self, metric_id=""):
        # print("################ JS rendering starting ################", metric_id)
        self.logger.warning(f"{metric_id}: Trying to render JS generated page using a headless browser")

        async def _run():
            page = None
            context = None
            try:
                # get a new browser context + page
                context = await BrowserManager._browser.new_context()
                page = await context.new_page()
                await page.goto(self.request_url)  # do not force wait strategy here
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except Exception as e:
                    self.logger.debug(f"{metric_id}: networkidle timeout ({e})")
                    pass  # many SPAs never become idle (polling / websockets)

                html = await page.content()
                return html
            except Exception as e:
                # print("############ page rendering error: ", e)
                self.logger.error(f"{metric_id}: Javascript page rendering error: E: " + str(e))

            finally:
                # clean up properly
                if page:
                    await page.close()
                if context:
                    await context.close()

        try:
            html = await _run()
            self.logger.info("FsF-F2-01M : Javascript page rendering finished")
            # print("################ JS rendering finished ################")
            return html

        except Exception as e:
            # self.logger.info("FsF-F2-01M : Javascript rendering failed: "+str(e))
            # print("################ JS rendering failed ################", e)
            self.logger.warning(f"{metric_id}: Rendering JS generated page failed: {e!s} : {self.request_url}")
            return None

    def _detect_mime_type(self):
        mime_type = self.response.content_type
        if mime_type is None and self.response.url:
            # print("RESPONS:", self.response.url, type(self.response.url))
            mime_type = mimetypes.guess_type(self.response.url, strict=True)[0]
        if mime_type is None:
            # just in case tika is not running use this as quick check for the most obvious
            try:
                if re.search(b"<!doctype html>|<html", self.response.content.strip(), re.IGNORECASE) is not None:
                    mime_type = "text/html"
            except Exception as e:
                print(e, "Request helper")
        # TIKA CONTENT TYPE DETECTION
        if mime_type is None:
            try:
                self.logger.info(
                    "%s : No content type (mime) given by server, trying to identify mime with TIKA " % self.metric_id
                )
                parsedFile = parser.from_buffer(self.response.content)
                mime_type = parsedFile.get("metadata").get("Content-Type")
            except Exception as e:
                self.logger.info("{} : TIKA content type guessing failed -: E: {} ".format(self.metric_id, str(e)))
                mime_type = "application/octet-stream"

        if "application/xhtml+xml" in mime_type:
            try:
                if re.search(b"<!doctype html>|<html", self.response.content.strip(), re.IGNORECASE) is None:
                    mime_type = "text/xml"
            except Exception as e:
                print(e, "Request helper")

        if "text/plain" in mime_type:
            self.logger.info(
                "%s : Plain text has been responded as content type, could be a RDF document! Trying to verify"
                % self.metric_id
            )
            # try to find type by url using rdflib
            if self.response.url:
                guessed_format = rdflib.util.guess_format(self.response.url)

                if guessed_format in self.rdf_type_dict:
                    mime_type = self.rdf_type_dict[guessed_format]

            mime_type = mime_type.split(";", 1)[0]

        return mime_type

    def _set_format_and_parsed_content(self):
        parsed_content = self.response.content
        format = MetadataFormats.HTML
        if self.response.content_type is not None:
            if "text/plain" in self.response.content_type:
                format = MetadataFormats.TEXT
            # elif self.response.content_type in ["application/xml", "text/xml"]:
            #        format = MetadataFormats.XML
            elif str(self.response.content_type).endswith("xml"):
                # in case the such a XML indeed is a RDF:
                root_element = ""
                try:
                    xmlparser = lxml.etree.XMLParser(strip_cdata=False, recover=True)
                    xmltree = lxml.etree.XML(self.response.content, xmlparser)
                    root_element = xmltree.tag
                    parsed_content = lxml.etree.tostring(xmltree)
                except Exception:
                    self.logger.warning("%s : Parsing XML document failed !" % self.metric_id)
                if re.match(r"(\{.+\})?RDF", root_element):
                    self.logger.info("%s : Expected XML but found RDF document by root tag!" % self.metric_id)
                    format = MetadataFormats.RDF
                else:
                    self.logger.info(
                        "%s : Found XML document based on responded content type: %s",
                        self.metric_id,
                        self.response.content_type,
                    )
                    format = MetadataFormats.XML
            elif self.response.content_type in self.rdf_type_dict.values():
                format = MetadataFormats.RDF
            elif "html" in self.response.content_type:
                format = MetadataFormats.HTML
            elif "json" in self.response.content_type:  # or "linkset" in self.response.content_type:
                parsed_content = json.loads(self.response.content)
                format = MetadataFormats.JSON

            # since we already parse HTML in the landing page we ignore this and do not parse again
            """if ignore_html is False:
                self.logger.info("%s : Found HTML page!" % metric_id)
            else:
                self.logger.info("%s : Ignoring HTML response" % metric_id)"""

        self.response.parsed_content = parsed_content
        self.response.parse_format = format
        return format, parsed_content

    def handle_content(self, metric_id, ignore_html):
        # format = MetadataFormats.HTML
        format = self.response.parse_format or MetadataFormats.HTML
        if self.response.content:
            # self.http_response = tp_response
            if self.response.headers.get("Content-Encoding") == "gzip":
                self.logger.info("FsF-F2-01M : Retrieving gzipped content")
                self.response.content = gzip.decompress(self.response.content)
            if self.response.headers.get("Content-Type") == "application/zip":
                self.logger.warning(
                    "FsF-F2-01M : Received zipped content which contains several files, therefore skipping tests"
                )
                self.response.content = None
                format = None
            """print(
                "{} : Content negotiation on {} accept={}, status={}, content-type={} ".format(
                    metric_id, self.request_url, self.accept_type, str(self.response.status), str(self.response.content_type)
                )
            )"""
            # key for content cache
            checked_content_id = hash(str(self.response.redirect_url) + str(self.response.content_type))
            # body is only loaded in case it is not yet in the cache for the given content type and url
            if checked_content_id in self.checked_content:
                self.checked_content_hash = checked_content_id
                format = self.checked_content.get(checked_content_id).get("format")
                self.response.parsed_content = self.checked_content.get(checked_content_id).get("parse_response")
                self.response.content = self.checked_content.get(checked_content_id).get("response_content")
                self.response.content_type = self.checked_content.get(checked_content_id).get("content_type")
                self.response.content_size = self.checked_content.get(checked_content_id).get("content_size")
                # content_truncated = self.checked_content.get(checked_content_id).get("content_truncated")
                # print('USING CACHE ...')
                self.logger.info(
                    "{} : Using Cached response content {} - {}".format(
                        metric_id, self.response.content_type, self.response.redirect_url
                    )
                )
            else:
                # self.logger.info("%s : Creating Cached response content" % metric_id)
                if self.response.status in [200]:
                    if self.response.truncated:
                        self.logger.warning(
                            "{} : Downloaded content has been TRUNCATED by F-UJI since it is larger than: -: {}".format(
                                metric_id, str(self.max_content_size)
                            )
                        )

                    if format:
                        # cache downloaded content
                        self.checked_content[checked_content_id] = {
                            "format": format,
                            "parse_response": self.response.parsed_content,
                            "response_content": self.response.content,
                            "content_type": self.response.content_type,
                            "content_size": self.response.content_size,
                            "content_truncated": self.response.truncated,
                        }
                    else:
                        self.logger.warning(f"{metric_id} : Content-type is NOT SPECIFIED")
                else:
                    self.logger.warning(
                        f"{metric_id} : NO successful response received, status code -: {self.response.status!s}"
                    )
        else:
            self.logger.warning(f"{metric_id} : No response received from -: {self.request_url}, {self.accept_type}")
        return format, self.response.parsed_content

    """async def content_negotiate(self, metric_id="", ignore_html=True, check_antibot=False):
        response = await self.request_content(metric_id, ignore_html, check_antibot)
        format = self.handle_content(response, metric_id, ignore_html)
        return format, self.parse_response"""

    async def content_negotiate(
        self,
        metric_id="",
        ignore_html=True,
        check_antibot=False,
    ):
        await self.request_content(
            metric_id=metric_id,
            check_antibot=check_antibot,
        )

        result = self.handle_content(
            metric_id=metric_id,
            ignore_html=ignore_html,
        )

        return result


##################### test ... to be deleted (later)
"""async def test():
    r = RequestHelper('http://www.w3id.org/example')
    r.setAcceptType(AcceptTypes.jsonld)
    neg_format, xml_response = await r.content_negotiate('Tset')
    print(r.response.content[:100])

asyncio.run(test())"""
