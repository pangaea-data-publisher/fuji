# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import io
import os
import re
import ssl
import threading
import urllib

import idutils
from tika import parser

from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.helper.request_helper import FUJIHTTPRedirectHandler


class DataHarvester:
    LOG_SUCCESS = 25
    LOG_FAILURE = 35

    def __init__(self, data_links, logger, landing_page=None, auth_token=None, auth_token_type="Basic", metrics=None):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; F-UJI)"
        self.logger = logger
        self.data_links = data_links
        self.auth_token = auth_token
        self.auth_token_type = auth_token_type
        self.metrics = metrics
        self.timeout = 10
        self.max_download_size = 1000000
        self.max_number_per_mime = 5
        self.data = {}
        self.landing_page = landing_page
        self.content_type = None
        self.delay_time = 3
        self.responses = {}

    def expand_url(self, url):
        # replace local urls with full path from landing_page URI
        self.logger.info("FsF-R1-01MD : Trying to complete local file name with full path info using landing page URI")
        if self.landing_page:
            if idutils.is_url(self.landing_page):
                try:
                    path = os.path.dirname(self.landing_page)
                    url = path + "/" + url
                except:
                    pass
        return url

    # in case experimental mime types are detected add mime types without x. or x. prefix
    def extend_mime_type_list(self, mime_list):
        if isinstance(mime_list, str):
            mime_list = [mime_list]
        for mime in mime_list:
            xm = re.split(r"/(?:[xX][-\.])?", mime)
            if len(xm) == 2:
                if str(xm[0] + "/" + xm[1]) not in mime_list:
                    mime_list.append(str(xm[0] + "/" + xm[1]))
        return mime_list

    def parse_content_size(self, size):
        try:
            bytematch = re.search(r"([0-9]+(?:[\.,][0-9]+)*)\s*([kMGTP]?(?:[Bb](?:ytes?)?))?", str(size))
            if bytematch:
                size = bytematch[1]
                mult = str(bytematch[2])
                size = float(size)
                if mult.startswith("k"):
                    size = size * 1000
                elif mult.startswith("M"):
                    size = size * 1000000
                elif mult.startswith("G"):
                    size = size * 1000000000
                elif mult.startswith("P"):
                    size = size * 1000000000000
        except Exception as e:
            print("Content site Byte parsing error: ", str(e))
        return size

    def retrieve_all_data(self, scan_content=True):
        # TODO: prioritise scientific files which can be opened by tika or other parsers for content analysis
        # choose sample of data_links which are accessible the smallest file per mime type (onbe per mime type)
        sorted_files = {}
        urls_to_check = {}
        # sort data links, here we trust the mime type given by the server
        if self.data_links:
            if isinstance(self.data_links, list):
                for fl in self.data_links:
                    # add more trust for more complete info
                    fl["trust"] = 0
                    if fl.get("size"):
                        fl["size"] = self.parse_content_size(fl["size"])
                        try:
                            float(fl["size"])
                            fl["trust"] += 1
                        except Exception:
                            fl["size"] = None
                    else:
                        fl["size"] = None
                    if fl.get("type") is None:
                        if fl["trust"] > 1:
                            fl["trust"] -= 1
                    elif "/" in str(fl.get("type")):
                        fl["trust"] += 1
                    if sorted_files.get(fl.get("type")):
                        sorted_files[fl.get("type")].append(fl)
                        sorted_files[fl.get("type")] = sorted(
                            sorted_files[fl.get("type")], key=lambda d: d["size"] if d.get("size") else float("inf")
                        )
                    else:
                        sorted_files[fl.get("type")] = [fl]

        # threaded download starts here
        for fmime, ft in sorted_files.items():
            timeout = 10
            if len(ft) > self.max_number_per_mime:
                self.logger.warning(
                    f"FsF-F3-01M : Found more than -: {self.max_number_per_mime!s} data links (out of {len(ft)!s}) of type {fmime} will only take {self.max_number_per_mime!s} for content analysis"
                )
            files_to_check = ft[: self.max_number_per_mime]
            # add the fifth one for compatibility reasons < f-uji 3.0.1, when we took the last of list of length FILES_LIMIT
            if len(self.data_links) >= 5:
                files_to_check.append(self.data_links[4])
            for f in files_to_check:
                url_trust = None
                if urls_to_check.get(f.get("url")):
                    url_trust = urls_to_check.get(f.get("url")).get("trust")
                if not url_trust:
                    url_trust = 0
                if f.get("url") and (not urls_to_check.get(f.get("url")) or url_trust < f.get("trust")):
                    urls_to_check[f.get("url")] = f
            # urls_to_check.extend([f.get('url') for f in ft[:self.max_number_per_mime]])
            # urls = [f.get('url') for f in ft[:self.max_number_per_mime]]
        e = threading.Event()
        if urls_to_check:
            # urls_to_check =list(set([u for u in urls_to_check if u]))
            threads = [
                threading.Thread(target=self.get_url_data_and_info, args=(url, timeout))
                for url in urls_to_check.values()
            ]
            for thread in threads:
                thread.start()
            for ti, thread in enumerate(threads):
                if ti > 0:
                    timeout = 1
                thread.join(timeout)
                if thread.is_alive():
                    e.set()
                thread.join()
                # thread ends here
                # print(self.data)
        return True

    def get_url_data_and_info(self, urldict, timeout):
        header = {"Accept": "*/*", "User-Agent": self.user_agent}
        if self.auth_token:
            header["Authorization"] = self.auth_token_type + " " + self.auth_token
        # header["Range"] = "bytes=0-" + str(self.max_download_size)
        url = urldict.get("url")
        if url:
            if not idutils.is_url(url):
                url = self.expand_url(url)
            # print("Downloading.. ", url)
            response = None
            redirect_status_list = []
            try:
                context = ssl._create_unverified_context()
                context.set_ciphers("DEFAULT@SECLEVEL=0")
                redirect_handler = FUJIHTTPRedirectHandler()
                opener = urllib.request.build_opener(
                    urllib.request.HTTPSHandler(context=context),
                    urllib.request.HTTPHandler(),
                    redirect_handler,
                )
                urllib.request.install_opener(opener)
                request = urllib.request.Request(url, headers=header)
                response = opener.open(request, timeout=10)
                # redirect_list = redirect_handler.redirect_list
                # redirect_status_list = redirect_handler.redirect_status_list
                # redirect_url = redirect_handler.redirect_url
                # request = urllib.request.Request(url, headers=header)
                # response = urllib.request.urlopen(request, timeout=timeout)
                self.responses[url] = response
                redirect_status_list = redirect_handler.status_list
            except urllib.error.HTTPError as e:
                self.logger.warning(f"FsF-F3-01M : Content identifier inaccessible -: {url}, HTTPError code {e.code} ")
                self.logger.warning(f"FsF-R1-01MD : Content identifier inaccessible -: {url}, HTTPError code {e.code} ")
                self.logger.warning(
                    f"FsF-R1.3-02D : Content identifier inaccessible -: {url}, HTTPError code {e.code} "
                )
                redirect_status_list = [int(e.code)]
            except urllib.error.URLError as e:
                self.logger.exception(e.reason)
                self.logger.warning(
                    f"FsF-F3-01M : Content identifier inaccessible -: {url}, URLError reason {e.reason} "
                )
                self.logger.warning(
                    f"FsF-R1-01MD : Content identifier inaccessible -: {url}, URLError reason {e.reason} "
                )
                self.logger.warning(
                    f"FsF-R1.3-02D : Content identifier inaccessible -: {url}, URLError reason {e.reason} "
                )
                redirect_status_list = redirect_handler.status_list
            except Exception as e:
                self.logger.warning("FsF-F3-01M : Content identifier inaccessible -:" + url + " " + str(e))
                self.logger.warning("FsF-R1-01MD : Content identifier inaccessible -:" + url + " " + str(e))
                self.logger.warning("FsF-R1.3-02D : Content identifier inaccessible -:" + url + " " + str(e))
                redirect_status_list = redirect_handler.status_list
            self.set_data_info(urldict, response, redirect_status_list)

    def set_data_info(self, urldict, response, redirect_status_list=[]):
        fileinfo = {}
        if isinstance(urldict, dict):
            fileinfo = {
                "url": urldict.get("url"),
                "claimed_size": urldict.get("size"),
                "claimed_type": urldict.get("type"),
                "claimed_service": urldict.get("service"),
                "claimed_profile": urldict.get("profile"),
                "content_size": 0,
                "truncated": False,
                "is_persistent": False,
                "status_list": redirect_status_list,
            }
            idhelper = IdentifierHelper(urldict.get("url"))
            if idhelper.preferred_schema:
                fileinfo["scheme"] = idhelper.preferred_schema
            if idhelper.is_persistent:
                fileinfo["is_persistent"] = True
            # response related info
            if response:
                file_buffer_object = io.BytesIO()
                rstatus = response.getcode()
                fileinfo["status_code"] = rstatus
                fileinfo["verified"] = False
                if fileinfo.get("status_code") == 200:
                    fileinfo["verified"] = True
                fileinfo["resolved_url"] = response.geturl()
                if response.headers.get("content-type"):
                    self.content_type = fileinfo["header_content_type"] = response.headers.get("content-type").split(
                        ";"
                    )[0]
                elif response.headers.get("Content-Type"):
                    self.content_type = fileinfo["header_content_type"] = response.headers.get("Content-Type").split(
                        ";"
                    )[0]
                if response.headers.get("content-length"):
                    fileinfo["header_content_size"] = response.headers.get("content-length").split(";")[0]
                elif response.headers.get("Content-Length"):
                    fileinfo["header_content_size"] = response.headers.get("Content-Length").split(";")[0]
                if fileinfo.get("header_content_size"):
                    try:
                        fileinfo["header_content_size"] = int(fileinfo["header_content_size"])
                    except:
                        fileinfo["header_content_size"] = self.max_download_size
                        pass
                content = response.read(self.max_download_size)
                file_buffer_object.write(content)
                fileinfo["content_size"] = file_buffer_object.getbuffer().nbytes
                if fileinfo.get("header_content_size"):
                    if fileinfo["content_size"] < fileinfo["header_content_size"]:
                        fileinfo["truncated"] = True
                if fileinfo["content_size"] > 0:
                    fileinfo.update(self.tika(file_buffer_object, urldict.get("url")))
            else:
                if len(fileinfo["status_list"]) > 0:
                    fileinfo["status_code"] = fileinfo["status_list"][-1]
            self.data[urldict.get("url")] = fileinfo
        return fileinfo

    def tika(self, file_buffer_object, url):
        parsed_content = ""
        tika_content_types = ""
        fileinfo = {"tika_content_type": []}
        status = None
        try:
            if len(file_buffer_object.getvalue()) > 0:
                parsedFile = parser.from_buffer(file_buffer_object.getvalue())
                fileinfo["tika_status"] = status = parsedFile.get("status")
                tika_content_types = parsedFile.get("metadata").get("Content-Type")
                parsed_content = parsedFile.get("content")
                self.logger.info("{} : Successfully parsed data object file using TIKA".format("FsF-R1-01MD"))
                file_buffer_object.close()
                parsedFile.clear()
            else:
                self.logger.warning("{} : Could not parse data object file using TIKA".format("FsF-R1-01MD"))

        except Exception as e:
            self.logger.warning("{} : File parsing using TIKA failed -: {}".format("FsF-R1-01MD", e))
            # in case TIKA request fails use response header info
            tika_content_types = str(self.content_type)

        if isinstance(tika_content_types, list):
            fileinfo["tika_content_type"] = list(set(i.split(";")[0] for i in tika_content_types))
        else:
            content_types_str = tika_content_types.split(";")[0]
            fileinfo["tika_content_type"].append(content_types_str)
        fileinfo["tika_content_type"] = self.extend_mime_type_list(fileinfo["tika_content_type"])

        # Extract the text content from the parsed file and convert to string
        self.logger.info("{} : File request status code -: {}".format("FsF-R1-01MD", status))

        fileinfo["test_data_content_text"] = str(re.sub(r"[\r\n\t\s]+", " ", str(parsed_content)))

        # Escape any slash # test_data_content_text = parsed_content.replace('\\', '\\\\').replace('"', '\\"')
        if fileinfo["test_data_content_text"]:
            self.logger.info(f"FsF-R1-01MD : Succesfully parsed data file(s) -: {url}")
        return fileinfo
