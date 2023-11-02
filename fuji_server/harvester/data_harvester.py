import io
import os
import re
import time
import urllib

import idutils
from tika import parser

from fuji_server.helper.identifier_helper import IdentifierHelper


class DataHarvester:
    LOG_SUCCESS = 25
    LOG_FAILURE = 35

    def __init__(self, data_links, logger, landing_page=None, auth_token=None, auth_token_type="Basic", metrics=None):
        self.logger = logger
        self.data_links = data_links
        self.auth_token = auth_token
        self.auth_token_type = auth_token_type
        self.metrics = metrics
        self.timeout = 10
        self.max_download_size = 1000000
        self.data = {}
        self.landing_page = landing_page
        self.content_type = None

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

    def retrieve_all_data_old(self, howmany=1):
        if self.data_links:
            if isinstance(self.data_links, list):
                self.data_links.reverse()
                if len(self.data_links) > howmany:
                    self.logger.warning(
                        "FsF-R1-01MD : Will not use all given data links, will use "
                        + str(howmany)
                        + " accessible data files from "
                        + (str(len(self.data_links)))
                    )
                inx = 0  # number of files which are not accessible (status code !=200)
                for idx, datafile in enumerate(self.data_links):
                    fileinfo = {}
                    if datafile.get("url") and idx < howmany + inx:
                        fileinfo, buffer = self.get(datafile.get("url"))
                        if fileinfo.get("status_code") != 200:
                            inx += 1
                        else:
                            fileinfo["verified"] = True
                        fileinfo["tika_content_type"] = []
                        if fileinfo:
                            fileinfo.update(self.tika(buffer, datafile.get("url")))
                    else:
                        fileinfo["verified"] = False
                    fileinfo["claimed_size"] = datafile.get("size")
                    fileinfo["claimed_type"] = datafile.get("type")
                    fileinfo["url"] = datafile.get("url")
                    self.data[datafile.get("url")] = fileinfo
        return True

    def retrieve_all_data(self):
        # rchoose sample of data_links which are accessible the smallest file per mime type (onbe per mime type)
        if self.data_links:
            if isinstance(self.data_links, list):
                sorted_files = {}
                for f in self.data_links:
                    if sorted_files.get(f.get("type")):
                        sorted_files[f.get("type")].append(f)
                        sorted_files[f.get("type")] = sorted(
                            sorted_files[f.get("type")], key=lambda d: d["size"] if d.get("size") else float("inf")
                        )
                    else:
                        sorted_files[f.get("type")] = [f]
                for ft in sorted_files.values():
                    for datafile in ft:
                        fileinfo, buffer = self.get(datafile.get("url"))
                        fileinfo["verified"] = False
                        if fileinfo.get("status_code") == 200:
                            fileinfo["verified"] = True
                        fileinfo["tika_content_type"] = []
                        if fileinfo:
                            fileinfo.update(self.tika(buffer, datafile.get("url")))
                        else:
                            fileinfo["verified"] = False
                        fileinfo["claimed_size"] = datafile.get("size")
                        fileinfo["claimed_type"] = datafile.get("type")
                        fileinfo["url"] = datafile.get("url")
                        if fileinfo["verified"]:
                            self.data[datafile.get("url")] = fileinfo
                            break
            # print('DATA', self.data)
        return True

    def get(self, url):
        start = time.time()
        fileinfo = {}
        downloaded_size = 0
        file_buffer_object = io.BytesIO()
        content_size = 0
        if url:
            fileinfo["is_persistent"] = False
            idhelper = IdentifierHelper(url)
            if idhelper.preferred_schema:
                fileinfo["schema"] = idhelper.preferred_schema
            if idhelper.is_persistent:
                fileinfo["is_persistent"] = True
            if not idutils.is_url(url):
                url = self.expand_url(url)
            try:
                request_headers = {"Accept": "*/*", "User-Agent": "F-UJI"}
                if self.auth_token:
                    request_headers["Authorization"] = self.auth_token_type + " " + self.auth_token
                request = urllib.request.Request(url, headers=request_headers)
                response = urllib.request.urlopen(request, timeout=self.timeout)
                rstatus = response.getcode()
                fileinfo["status_code"] = rstatus
                fileinfo["truncated"] = False
                fileinfo["resolved_url"] = response.geturl()
                # self.info['response_content_type'] = content_type = response.info().get_content_type()
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

                chunksize = 1024
                content_size = 0
                while True:
                    chunk = response.read(chunksize)
                    if not chunk:
                        break
                    else:
                        # response_body.append(chunk)
                        file_buffer_object.write(chunk)
                        # avoiding large file sizes to test with TIKA.. truncate after 1 Mb
                        fileinfo["downloaded_size"] = downloaded_size = downloaded_size + len(chunk)
                        if time.time() > (start + self.timeout) or downloaded_size >= self.max_download_size:
                            self.logger.warning(
                                "FsF-R1-01MD : File too large.., skipped download after -:"
                                + str(self.timeout)
                                + " sec or receiving > "
                                + str(self.max_download_size)
                                + f"- {url}"
                            )
                            content_size = 0
                            content_size = str(response.headers.get("content-length")).split(";")[0]
                            fileinfo["truncated"] = True

                            break
                        else:
                            content_size = downloaded_size
                        fileinfo["content_size"] = content_size
                response.close()
                self.logger.warning(f"FsF-R1-01MD : Content identifier accessible -: {url}, HTTPStatus code {rstatus} ")

            except urllib.error.HTTPError as e:
                self.logger.warning(f"FsF-F3-01M : Content identifier inaccessible -: {url}, HTTPError code {e.code} ")
                self.logger.warning(f"FsF-R1-01MD : Content identifier inaccessible -: {url}, HTTPError code {e.code} ")
                self.logger.warning(
                    f"FsF-R1.3-02D : Content identifier inaccessible -: {url}, HTTPError code {e.code} "
                )
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
            except Exception as e:
                self.logger.warning("FsF-F3-01M : Content identifier inaccessible -:" + url + " " + str(e))
                self.logger.warning("FsF-R1-01MD : Content identifier inaccessible -:" + url + " " + str(e))
                self.logger.warning("FsF-R1.3-02D : Content identifier inaccessible -:" + url + " " + str(e))
        return fileinfo, file_buffer_object

    def tika(self, file_buffer_object, url):
        parsed_content = ""
        tika_content_types = ""
        fileinfo = {"tika_content_type": []}
        status = None
        try:
            if len(file_buffer_object.getvalue()) > 0:
                parsedFile = parser.from_buffer(file_buffer_object.getvalue())
                # print('TIKA: ',url, parsedFile)
                # if not parsedFile.get('content'):
                #    print('NO CONTENT')
                # else:
                #    print('HAS CONTENT')
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
