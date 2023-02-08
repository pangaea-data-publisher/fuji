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
import io
import re
import sys
import urllib
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.data_content_metadata import DataContentMetadata
from fuji_server.models.data_content_metadata_output import DataContentMetadataOutput
from fuji_server.models.data_content_metadata_output_inner import DataContentMetadataOutputInner
import time
from tika import parser


class FAIREvaluatorDataContentMetadata(FAIREvaluator):
    """
    A class to evaluate whether the metadata specifies the content of the data (R1.01MD). A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate the metadata that specifies the content of the data, e.g., resource type and links. In addition, the metadata includes
        verifiable data descriptor file info (size and type) and the measured variables observation types will also be evaluated.
    """

    def evaluate(self):
        self.result = DataContentMetadata(id=self.metric_number,
                                          metric_identifier=self.metric_identifier,
                                          metric_name=self.metric_name)
        self.output = DataContentMetadataOutput()
        data_content_descriptors = []
        test_data_content_text = None
        test_data_content_url = None
        test_status = 'fail'
        score = 0

        self.logger.info('FsF-R1-01MD : Object landing page accessible status -: {}'.format(
            self.fuji.isLandingPageAccessible))

        # 1. check resource type #TODO: resource type collection might be classified as 'dataset'
        # http://doi.org/10.1007/s10531-013-0468-6
        #
        resource_type = self.fuji.metadata_merged.get('object_type')
        if resource_type:
            resource_type = str(resource_type).lower()
            if str(resource_type).startswith('http'):
                resource_type = '/'.join(str(resource_type).split('/')[-2:])
            if resource_type in self.fuji.VALID_RESOURCE_TYPES or resource_type in self.fuji.SCHEMA_ORG_CONTEXT:
                self.logger.log(self.fuji.LOG_SUCCESS,
                                'FsF-R1-01MD : Resource type specified -: {}'.format(resource_type))
                self.output.object_type = resource_type
                self.setEvaluationCriteriumScore('FsF-R1-01MD-1', 1, 'pass')
                self.setEvaluationCriteriumScore('FsF-R1-01MD-1a', 0, 'pass')
                self.maturity = 1
                score += 1
            else:
                self.logger.warning('FsF-R1-01MD : No valid resource type specified -: ' + str(resource_type))
        else:
            self.logger.warning('FsF-R1-01MD : NO resource type specified ')

        # 2. initially verification is restricted to the last file and only use object content uri that is accessible (self.content_identifier)
        if isinstance(self.fuji.content_identifier, list):
            if len(self.fuji.content_identifier) > 0:
                self.maturity = 1
                self.setEvaluationCriteriumScore('FsF-R1-01MD-1', 1, 'pass')
                self.setEvaluationCriteriumScore('FsF-R1-01MD-1b', 0, 'pass')
            not_empty_content_uris = [d['url'] for d in self.fuji.content_identifier if 'url' in d]
            content_length = len(not_empty_content_uris)
            if content_length > 0:
                if self.maturity < 3:
                    self.maturity = 2
                self.logger.info('FsF-R1-01MD : Number of data content URI(s) specified -: {}'.format(content_length))
                test_data_content_url = not_empty_content_uris[-1]
                self.logger.info(
                    'FsF-R1-01MD : Selected content file to be analyzed -: {}'.format(test_data_content_url))
                try:
                    # Use Tika to parse the file
                    response_content = None
                    response_body = []
                    timeout = 10
                    tika_content_size = 0
                    max_download_size = 1000000
                    file_buffer_object = io.BytesIO()
                    start = time.time()
                    #r = requests.get(test_data_content_url, verify=False, stream=True)
                    try:
                        request_headers = {
                            'Accept': '*/*',
                            'User-Agent': 'F-UJI'}
                        if self.fuji.auth_token:
                            request_headers['Authorization'] = self.fuji.auth_token_type+' '+self.fuji.auth_token
                        request = urllib.request.Request(test_data_content_url, headers=request_headers)
                        response = urllib.request.urlopen(request, timeout=10)

                        content_type = response.info().get_content_type()
                        header_content_types = response.headers.get('content-type')
                        chunksize = 1024
                        while True:
                            chunk = response.read(chunksize)
                            if not chunk:
                                break
                            else:
                                #response_body.append(chunk)
                                file_buffer_object.write(chunk)
                                # avoiding large file sizes to test with TIKA.. truncate after 1 Mb
                                tika_content_size = tika_content_size + len(chunk)
                                if time.time() > (start + timeout) or tika_content_size >= max_download_size:
                                    self.logger.warning('FsF-R1-01MD : File too large.., skipped download after -:' +
                                                        str(timeout) + ' sec or receiving > ' + str(max_download_size) +
                                                        '- {}'.format(test_data_content_url))
                                    tika_content_size = 0
                                    tika_content_size = str(response.headers.get('content-length')).split(';')[0]
                                    break
                        response.close()

                    except urllib.error.HTTPError as e:
                        self.logger.warning(
                            'FsF-F3-01M : Content identifier inaccessible -: {0}, HTTPError code {1} '.format(
                                test_data_content_url, e.code))
                        self.logger.warning(
                            'FsF-R1-01MD : Content identifier inaccessible -: {0}, HTTPError code {1} '.format(
                                test_data_content_url, e.code))
                        self.logger.warning(
                            'FsF-R1.3-02D : Content identifier inaccessible -: {0}, HTTPError code {1} '.format(
                                test_data_content_url, e.code))
                    except urllib.error.URLError as e:
                        self.logger.exception(e.reason)
                        self.logger.warning('FsF-F3-01M : Content identifier inaccessible -: {0}, URLError reason {1} '.format(
                                test_data_content_url, e.reason))
                        self.logger.warning('FsF-R1-01MD : Content identifier inaccessible -: {0}, URLError reason {1} '.format(
                                test_data_content_url, e.reason))
                        self.logger.warning('FsF-R1.3-02D : Content identifier inaccessible -: {0}, URLError reason {1} '.format(
                                test_data_content_url, e.reason))

                    except Exception as e:
                        self.logger.warning('FsF-F3-01M : Content identifier inaccessible -:' + str(e))
                        self.logger.warning('FsF-R1-01MD : Content identifier inaccessible -:' + str(e))
                        self.logger.warning('FsF-R1.3-02D : Content identifier inaccessible -:' + str(e))


                    status = 'tika error'
                    parsed_content = ''
                    tika_content_types = ''
                    try:
                        if len(file_buffer_object.getvalue()) > 0:
                            parsedFile = parser.from_buffer(file_buffer_object.getvalue())
                            status = parsedFile.get('status')
                            tika_content_types = parsedFile.get('metadata').get('Content-Type')
                            parsed_content = parsedFile.get('content')
                            self.logger.info('{0} : Successfully parsed data object file using TIKA'.format(
                                self.metric_identifier))
                            file_buffer_object.close()
                            parsedFile.clear()
                        else:
                            self.logger.warning('{0} : Could not parse data object file using TIKA'.format(
                                self.metric_identifier))

                    except Exception as e:
                        self.logger.warning('{0} : File parsing using TIKA failed -: {1}'.format(
                            self.metric_identifier, e))
                        # in case TIKA request fails use response header info
                        tika_content_types = str(header_content_types).split(';')[0]

                    if isinstance(tika_content_types, list):
                        self.fuji.tika_content_types_list = list(set(i.split(';')[0] for i in tika_content_types))
                    else:
                        content_types_str = tika_content_types.split(';')[0]
                        self.fuji.tika_content_types_list.append(content_types_str)

                    # Extract the text content from the parsed file and convert to string
                    self.logger.info('{0} : File request status code -: {1}'.format(self.metric_identifier, status))

                    test_data_content_text = str(parsed_content)

                    # Escape any slash # test_data_content_text = parsed_content.replace('\\', '\\\\').replace('"', '\\"')
                    if test_data_content_text:
                        self.logger.info(
                            'FsF-R1-01MD : Succesfully parsed data file(s) -: {}'.format(test_data_content_url))
                #else:
                #    self.logger.warning('FsF-R1-01MD : Data file not accessible {}'.format(r.status_code))
                except Exception as e:
                    self.logger.warning('{0} : Could not retrieve/parse content object -: {1}'.format(
                        self.metric_identifier, e))
            else:
                self.logger.warning(
                    'FsF-R1-01MD : NO data object content available/accessible to perform file descriptors (type and size) tests'
                )

        # 3. check file type and size descriptors of parsed data file only (ref:test_data_content_url)
        if test_data_content_url:
            descriptors = [
                'type', 'size'
            ]  # default keys ['url', 'type', 'size', 'profile', 'header_content_type', 'header_content_length']
            data_object = next(item for item in self.fuji.metadata_merged.get('object_content_identifier')
                               if item.get('url') == test_data_content_url)
            if data_object.get('type') and data_object.get('size'):
                score += 1
                if self.maturity < 3:
                    self.maturity = 2
                self.setEvaluationCriteriumScore('FsF-R1-01MD-2', 1, 'pass')
                self.setEvaluationCriteriumScore('FsF-R1-01MD-2a', 0, 'pass')

            matches_type = False
            matches_size = False

            for d in descriptors:
                type = 'file ' + d
                if d in data_object.keys() and data_object.get(d):
                    descriptor = type
                    descriptor_value = data_object.get(d)
                    matches_content = False

                    #if data_object.get('header_content_type') == data_object.get('type'):
                    # TODO: variation of mime type (text/tsv vs text/tab-separated-values)
                    self.fuji.tika_content_types_list = self.fuji.extend_mime_type_list(self.fuji.tika_content_types_list)
                    if d == 'type':
                        if data_object.get('type'):
                            if data_object.get('type') in self.fuji.tika_content_types_list:
                                matches_content = True
                                matches_type = True
                            else:
                                self.logger.warning(
                                    '{0} : Could not verify content type from downloaded file -: (expected: {1}, found: {2})'
                                    .format(self.metric_identifier, data_object.get('type'),
                                            str(self.fuji.tika_content_types_list)))
                                self.fuji.tika_content_types_list.append('unverified')
                    elif d == 'size':
                        if tika_content_size == 0:
                            self.logger.warning(
                                '{0} : Could not verify content size (received: 0 bytes) from downloaded file'.format(
                                    self.metric_identifier))
                        else:
                            try:
                                if data_object.get('size'):
                                    data_size = data_object.get('size')
                                    try:
                                        dsm =  re.match(r"(\d+(?:\.\d+)?)\s*[A-Za-z]*", str(data_size))
                                        if dsm[1]:
                                            data_size = dsm[1]
                                    except:
                                        pass
                                    object_size = int(float(data_size))
                                    if object_size == int(float(tika_content_size)):
                                        matches_content = True
                                        matches_size = True
                                    else:
                                        self.logger.warning(
                                            '{0} : Could not verify content size from downloaded file -: (expected: {1}, found: {2})'
                                            .format(self.metric_identifier, str(data_object.get('size')),
                                                    str(tika_content_size)))

                            except Exception as e:
                                print(e)
                                self.logger.warning(
                                    '{0} : Could not verify content size from downloaded file -: (expected: {1}, found: {2})'
                                    .format(self.metric_identifier, str(data_object.get('size')),
                                            str(tika_content_size)))

                    data_content_filetype_inner = DataContentMetadataOutputInner()
                    data_content_filetype_inner.descriptor = descriptor
                    data_content_filetype_inner.descriptor_value = descriptor_value
                    data_content_filetype_inner.matches_content = matches_content
                    data_content_descriptors.append(data_content_filetype_inner)
                else:
                    self.logger.warning('{0} : NO info about {1} available in given metadata -: '.format(
                        self.metric_identifier, type))
            ### scoring for file descriptors match
            if matches_type and matches_size:
                score += 1
                self.maturity = 3
                self.setEvaluationCriteriumScore('FsF-R1-01MD-3', 1, 'pass')

        # 4. check if varibles specified in the data file
        is_variable_scored = False
        if self.fuji.metadata_merged.get('measured_variable'):
            self.setEvaluationCriteriumScore('FsF-R1-01MD-2', 1, 'pass')
            self.setEvaluationCriteriumScore('FsF-R1-01MD-2b', 0, 'pass')
            self.logger.log(
                self.fuji.LOG_SUCCESS,
                'FsF-R1-01MD : Found measured variables or observations (aka parameters) as content descriptor')
            if self.maturity < 3:
                self.maturity = 2
            if not test_data_content_text:
                self.logger.warning(
                    'FsF-R1-01MD : Could not verify measured variables found in data object content, content parsing failed'
                )
            for variable in self.fuji.metadata_merged['measured_variable']:
                variable_metadata_inner = DataContentMetadataOutputInner()
                variable_metadata_inner.descriptor = 'measured_variable'
                variable_metadata_inner.descriptor_value = variable
                if test_data_content_text:
                    if variable in test_data_content_text:  # TODO use rapidfuzz (fuzzy search)
                        # self.logger.info('FsF-R1-01MD : Measured variable found in file content - {}'.format(variable))
                        variable_metadata_inner.matches_content = True
                        if not is_variable_scored:  # only increase once
                            self.setEvaluationCriteriumScore('FsF-R1-01MD-4', 1, 'pass')
                            self.logger.log(self.fuji.LOG_SUCCESS,
                                            'FsF-R1-01MD : Found specified measured variable in data object content')
                            self.maturity = 3
                            score += 1
                            is_variable_scored = True
                data_content_descriptors.append(variable_metadata_inner)
        else:
            self.logger.warning(
                'FsF-R1-01MD : NO measured variables found in metadata, skip \'measured_variable\' test.')
        if not is_variable_scored:
            self.logger.warning('FsF-R1-01MD : Measured variables given in metadata do not match data object content')

        if score >= self.total_score / 2:  # more than half of total score, consider the test as pass
            test_status = 'pass'
        self.output.data_content_descriptor = data_content_descriptors
        self.result.output = self.output
        self.score.earned = score
        self.result.score = self.score
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.test_status = test_status
