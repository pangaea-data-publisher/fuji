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

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.data_content_metadata import DataContentMetadata
from fuji_server.models.data_content_metadata_output import DataContentMetadataOutput
from fuji_server.models.data_content_metadata_output_inner import DataContentMetadataOutputInner

from tika import parser

class FAIREvaluatorDataContentMetadata(FAIREvaluator):
    def evaluate(self):

        self.result = DataContentMetadata(id=self.fuji.count,
                                                           metric_identifier=self.metric_identifier,
                                                           metric_name=self.metric_name)
        self.output = DataContentMetadataOutput()
        data_content_descriptors = []
        test_data_content_text = None
        test_data_content_url = None
        test_status = 'fail'
        score = 0

        self.logger.info('FsF-R1-01MD : Object landing page accessible status - {}'.format(self.fuji.isMetadataAccessible))

        # 1. check resource type #TODO: resource type collection might be classified as 'dataset'
        resource_type = self.fuji.metadata_merged.get('object_type')
        if resource_type:
            self.logger.info('FsF-R1-01MD : Resource type specified - {}'.format(resource_type))
            self.output.object_type = resource_type
            score += 1
        else:
            self.logger.warning('FsF-R1-01MD : NO resource type specified ')

        # 2. initially verification is restricted to the first file and only use object content uri that is accessible (self.content_identifier)
        if isinstance(self.fuji.content_identifier, list):
            content_uris = [d['url'] for d in self.fuji.content_identifier if 'url' in d]
            content_length = len(self.fuji.content_identifier)
            if content_length > 0:
                self.logger.info('FsF-R1-01MD : Number of data content URI(s) specified - {}'.format(content_length))
                test_data_content_url = self.fuji.content_identifier[-1].get('url')
                self.logger.info(
                    'FsF-R1-01MD : Selected content file to be analyzed - {}'.format(test_data_content_url))
                try:
                    # Use Tika to parse the file
                    parsedFile = parser.from_file(test_data_content_url)
                    status = parsedFile.get("status")
                    tika_content_types = parsedFile.get("metadata").get('Content-Type')
                    if isinstance(tika_content_types, list):
                        self.fuji.tika_content_types_list = list(set(i.split(';')[0] for i in tika_content_types))
                    else:
                        content_types_str = tika_content_types.split(';')[0]
                        self.fuji.tika_content_types_list.append(content_types_str)

                    # Extract the text content from the parsed file and convert to string
                    self.logger.info(
                        '{0} : File request status code {1}'.format(self.metric_identifier, status))
                    parsed_content = parsedFile["content"]
                    test_data_content_text = str(parsed_content)
                    # Escape any slash # test_data_content_text = parsed_content.replace('\\', '\\\\').replace('"', '\\"')
                    if test_data_content_text:
                        parsed_files = parsedFile.get("metadata").get('resourceName')
                        self.logger.info('FsF-R1-01MD : Succesfully parsed data file(s) - {}'.format(parsed_files))
                except Exception as e:
                    self.logger.warning(
                        '{0} : Could not retrive/parse content object - {1}'.format(self.metric_identifier,
                                                                                    e))
            else:
                self.logger.warning(
                    'FsF-R1-01MD : NO data object content available/accessible to perform file descriptors (type and size) tests')

        # 3. check file type and size descriptors of parsed data file only (ref:test_data_content_url)
        if test_data_content_url:
            descriptors = ['type',
                           'size']  # default keys ['url', 'type', 'size', 'profile', 'header_content_type', 'header_content_length']
            data_object = next(item for item in self.fuji.metadata_merged.get('object_content_identifier') if
                               item["url"] == test_data_content_url)
            missing_descriptors = []
            for d in descriptors:
                type = 'file ' + d
                if d in data_object.keys() and data_object.get(d):
                    descriptor = type
                    descriptor_value = data_object.get(d)
                    matches_content = False
                    if data_object.get('header_content_type') == data_object.get(
                            'type'):  # TODO: variation of mime type (text/tsv vs text/tab-separated-values)
                        matches_content = True
                        score += 1
                    data_content_filetype_inner = DataContentMetadataOutputInner()
                    data_content_filetype_inner.descriptor = descriptor
                    data_content_filetype_inner.descriptor_value = descriptor_value
                    data_content_filetype_inner.matches_content = matches_content
                    data_content_descriptors.append(data_content_filetype_inner)
                else:
                    self.logger.warning('{0} : NO {1} info available'.format(self.metric_identifier, type))

        # 4. check if varibles specified in the data file
        is_variable_scored = False
        if self.fuji.metadata_merged.get('measured_variable'):
            self.logger.info(
                'FsF-R1-01MD : Found measured variables or observations (aka parameters) as content descriptor')
            if test_data_content_text:
                for variable in self.fuji.metadata_merged['measured_variable']:
                    variable_metadata_inner = DataContentMetadataOutputInner()
                    variable_metadata_inner.descriptor = 'measured_variable'
                    variable_metadata_inner.descriptor_value = variable
                    if variable in test_data_content_text:  # TODO use rapidfuzz (fuzzy search)
                        # self.logger.info('FsF-R1-01MD : Measured variable found in file content - {}'.format(variable))
                        variable_metadata_inner.matches_content = True
                        if not is_variable_scored:  # only increase once
                            score += 1
                            is_variable_scored = True
                    data_content_descriptors.append(variable_metadata_inner)
        else:
            self.logger.warning(
                'FsF-R1-01MD : NO measured variables found in metadata, skip \'measured_variable\' test.')

        if score >= self.total_score / 2:  # more than half of total score, consider the test as pass
            test_status = 'pass'
        self.output.data_content_descriptor = data_content_descriptors
        self.result.output = self.output
        self.score.earned = score
        self.result.score = self.score
        self.result.test_status = test_status