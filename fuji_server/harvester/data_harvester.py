import hashlib
import io
import logging
import re
import time
import urllib
from tika import parser

class DataHarvester():
    LOG_SUCCESS = 25
    LOG_FAILURE = 35
    def __init__(self, data_links, logger, auth_token=None, auth_token_type='Basic', metrics = None):
        self.logger = logger
        self.data_links = data_links
        self.auth_token = auth_token
        self.auth_token_type = auth_token_type
        self.metrics = metrics
        self.timeout = 10
        self.max_download_size = 1000000
        self.data = {}

    # in case experimental mime types are detected add mime types without x. or x. prefix
    def extend_mime_type_list(self, mime_list):
        if isinstance(mime_list, str):
            mime_list = [mime_list]
        for mime in mime_list:
            xm = re.split(r'/(?:[xX][-\.])?', mime)
            if len(xm) == 2:
                if str(xm[0] + '/' + xm[1]) not in mime_list:
                    mime_list.append(str(xm[0] + '/' + xm[1]))
        return mime_list

    def retrieve_all_data(self, range = None):
        if self.data_links:
            for datafile in self.data_links:
                if datafile.get('url'):
                    fileinfo, buffer = self.get(datafile.get('url'))
                    if fileinfo:
                        fileinfo.update(self.tika(buffer, datafile.get('url')))
                    fileinfo['claimed_size'] = datafile.get('size')
                    fileinfo['claimed_type'] = datafile.get('type')
                    fileinfo['url'] = datafile.get('url')
                    fileinfo['tika_content_type'] = []
                    self.data[datafile.get('url')]=fileinfo
        return True
                
    def get(self,url):
        start = time.time()
        fileinfo = {}
        downloaded_size = 0
        file_buffer_object = io.BytesIO()
        content_size = 0
        if url:
            try:
                request_headers = {
                    'Accept': '*/*',
                    'User-Agent': 'F-UJI'}
                if self.auth_token:
                    request_headers['Authorization'] = self.auth_token_type + ' ' + self.auth_token
                request = urllib.request.Request(url, headers=request_headers)
                response = urllib.request.urlopen(request, timeout=self.timeout)
    
                #self.info['response_content_type'] = content_type = response.info().get_content_type()
                self.content_type = fileinfo['header_content_type'] = response.headers.get('content-type').split(';')[0]
                chunksize = 1024
                while True:
                    chunk = response.read(chunksize)
                    if not chunk:
                        break
                    else:
                        # response_body.append(chunk)
                        file_buffer_object.write(chunk)
                        # avoiding large file sizes to test with TIKA.. truncate after 1 Mb
                        fileinfo['downloaded_size'] = downloaded_size = downloaded_size + len(chunk)
                        if time.time() > (start + self.timeout) or downloaded_size >= self.max_download_size:
                            self.logger.warning('FsF-R1-01MD : File too large.., skipped download after -:' +
                                                str(self.timeout) + ' sec or receiving > ' + str(self.max_download_size) +
                                                '- {}'.format(self.url))
                            content_size = 0
                            content_size = str(response.headers.get('content-length')).split(';')[0]
                            break
                        else:
                            content_size = downloaded_size
                        fileinfo['content_size'] = content_size
                response.close()

            except urllib.error.HTTPError as e:
                print('ERROR1: ',e)
                self.logger.warning(
                    'FsF-F3-01M : Content identifier inaccessible -: {0}, HTTPError code {1} '.format(
                        url, e.code))
                self.logger.warning(
                    'FsF-R1-01MD : Content identifier inaccessible -: {0}, HTTPError code {1} '.format(
                        url, e.code))
                self.logger.warning(
                    'FsF-R1.3-02D : Content identifier inaccessible -: {0}, HTTPError code {1} '.format(
                        url, e.code))
            except urllib.error.URLError as e:
                print('ERROR2: ', e)
                self.logger.exception(e.reason)
                self.logger.warning('FsF-F3-01M : Content identifier inaccessible -: {0}, URLError reason {1} '.format(
                    url, e.reason))
                self.logger.warning('FsF-R1-01MD : Content identifier inaccessible -: {0}, URLError reason {1} '.format(
                    url, e.reason))
                self.logger.warning('FsF-R1.3-02D : Content identifier inaccessible -: {0}, URLError reason {1} '.format(
                    url, e.reason))
            except Exception as e:
                print('ERROR3: ', e)
                self.logger.warning('FsF-F3-01M : Content identifier inaccessible -:' +url +' '+ str(e))
                self.logger.warning('FsF-R1-01MD : Content identifier inaccessible -:' + url +' '+ str(e))
                self.logger.warning('FsF-R1.3-02D : Content identifier inaccessible -:' +url +' '+ str(e))
        return fileinfo, file_buffer_object

    def tika(self, file_buffer_object, url):
        parsed_content = ''
        tika_content_types = ''
        fileinfo={'tika_content_type':[]}
        try:
            if len(file_buffer_object.getvalue()) > 0:
                parsedFile = parser.from_buffer(file_buffer_object.getvalue())
                fileinfo['tika_status'] = status = parsedFile.get('status')
                tika_content_types = parsedFile.get('metadata').get('Content-Type')
                parsed_content = parsedFile.get('content')
                self.logger.info('{0} : Successfully parsed data object file using TIKA'.format(
                    'FsF-R1-01MD'))
                file_buffer_object.close()
                parsedFile.clear()
            else:
                self.logger.warning('{0} : Could not parse data object file using TIKA'.format(
                    'FsF-R1-01MD'))

        except Exception as e:
            self.logger.warning('{0} : File parsing using TIKA failed -: {1}'.format(
                'FsF-R1-01MD', e))
            # in case TIKA request fails use response header info
            tika_content_types = str(self.content_type)

        if isinstance(tika_content_types, list):
            fileinfo['tika_content_type'] = list(set(i.split(';')[0] for i in tika_content_types))
        else:
            content_types_str = tika_content_types.split(';')[0]
            fileinfo['tika_content_type'].append(content_types_str)
        fileinfo['tika_content_type'] = self.extend_mime_type_list(fileinfo['tika_content_type'])

        # Extract the text content from the parsed file and convert to string
        self.logger.info('{0} : File request status code -: {1}'.format('FsF-R1-01MD', status))

        fileinfo['test_data_content_text'] = str(re.sub(r'[\r\n\t\s]+', ' ', str(parsed_content)))

        # Escape any slash # test_data_content_text = parsed_content.replace('\\', '\\\\').replace('"', '\\"')
        if fileinfo['test_data_content_text']:
            self.logger.info(
                'FsF-R1-01MD : Succesfully parsed data file(s) -: {}'.format(url))
        return fileinfo

