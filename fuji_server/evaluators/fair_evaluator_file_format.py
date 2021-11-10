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

from fuji_server.models.data_file_format import DataFileFormat
from fuji_server.models.data_file_format_output import DataFileFormatOutput
from fuji_server.models.data_file_format_output_inner import DataFileFormatOutputInner
import mimetypes
import re


class FAIREvaluatorFileFormat(FAIREvaluator):
    """
    A class to evaluate whether the data is available in a file format recommended by the targe research community (R1.3-02D).
    A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate whether the data format is available in a long-term format (as defined in ISO/TR 22299)
        or in open format (see e.g., https://en.wikipedia.org/wiki/List_of_open_formats) or in a scientific file format.
    """
    def evaluate(self):

        text_format_regex = r'(^text)[\/]|[\/\+](xml|text|json)'

        self.result = DataFileFormat(id=self.metric_number,
                                     metric_identifier=self.metric_identifier,
                                     metric_name=self.metric_name)
        self.output = DataFileFormatOutput()
        data_file_list = []

        if not self.fuji.content_identifier:  # self.content_identifier only includes uris that are accessible
            contents = self.fuji.metadata_merged.get('object_content_identifier')
            unique_types = []
            if contents:
                for c in contents:
                    if c.get('type'):
                        unique_types.append(c.get('type'))
                self.logger.info('FsF-R1.3-02D : File format(s) specified -: {}'.format(list(set(unique_types))))

        mime_url_pair = {}
        if len(self.fuji.content_identifier) > 0:
            content_urls = [item.get('url') for item in self.fuji.content_identifier]
            self.logger.info('FsF-R1.3-02D : Data content identifier provided -: {}'.format(content_urls))
            #self.maturity = 1

            preferred_detected = False
            for file_index, data_file in enumerate(self.fuji.content_identifier):

                mime_type = data_file.get('type')
                if data_file.get('url') is not None:
                    if mime_type is None or mime_type in ['application/octet-stream', 'binary/octet-stream']:
                        self.logger.info(
                            'FsF-R1.3-02D : Guessing  the type of a file based on its filename or URL -: {}'.format(
                                data_file.get('url')))
                        # if mime type not given try to guess it based on the file name
                        guessed_mime_type = mimetypes.guess_type(data_file.get('url'))
                        self.logger.info('FsF-R1.3-02D : Guess return value -: {}'.format(guessed_mime_type))
                        mime_type = guessed_mime_type[
                            0]  # the return value is a tuple (type, encoding) where type is None if the type can’t be guessed

                    if mime_type:
                        if mime_type in self.fuji.ARCHIVE_MIMETYPES:  # check archive&compress media type
                            self.logger.info(
                                'FsF-R1.3-02D : Archiving/compression format specified -: {}'.format(mime_type))
                            if 'unverified' not in self.fuji.tika_content_types_list:
                                # exclude archive format
                                if file_index == len(self.fuji.content_identifier) - 1:
                                    self.fuji.tika_content_types_list = [
                                        n for n in self.fuji.tika_content_types_list
                                        if n not in self.fuji.ARCHIVE_MIMETYPES
                                    ]
                                    self.logger.info(
                                        'FsF-R1.3-02D : Extracted file formats for selected data object (see FsF-R1-01MD) -: {}'
                                        .format(self.fuji.tika_content_types_list))
                                    for t in self.fuji.tika_content_types_list:
                                        mime_url_pair[t] = data_file.get('url')
                            else:
                                self.logger.warning(
                                    'FsF-R1.3-02D : Content type not verified during FsF-R1-01MD, assuming login page or similar instead of -: {}'
                                    .format(mime_type))
                        else:
                            mime_url_pair[mime_type] = data_file.get('url')
                            if self.fuji.tika_content_types_list:
                                #add tika detected mimes
                                for tika_mime in self.fuji.tika_content_types_list:
                                    if tika_mime != 'unverified' and tika_mime not in mime_url_pair:
                                        mime_url_pair[tika_mime] = data_file.get('url')

            # FILE FORMAT CHECKS....
            # check if format is a scientific one:

            for mimetype, url in mime_url_pair.items():
                data_file_output = DataFileFormatOutputInner()
                preferance_reason = []
                subject_area = []
                if mimetype in self.fuji.SCIENCE_FILE_FORMATS:
                    self.setEvaluationCriteriumScore('FsF-R1.3-02D-1c', 0, 'pass')
                    if self.maturity < 3:
                        self.maturity = 3
                    if self.fuji.SCIENCE_FILE_FORMATS.get(mimetype) == 'Generic':
                        subject_area.append('General')
                        preferance_reason.append('generic science format')
                    else:
                        subject_area.append(self.fuji.SCIENCE_FILE_FORMATS.get(mimetype))
                        preferance_reason.append('science format')
                    data_file_output.is_preferred_format = True
                # check if long term format
                if mimetype in self.fuji.LONG_TERM_FILE_FORMATS:
                    self.setEvaluationCriteriumScore('FsF-R1.3-02D-1b', 0, 'pass')
                    if self.maturity < 2:
                        self.maturity = 2
                    preferance_reason.append('long term format')
                    subject_area.append('General')
                    data_file_output.is_preferred_format = True
                # check if open format
                if mimetype in self.fuji.OPEN_FILE_FORMATS:
                    self.setEvaluationCriteriumScore('FsF-R1.3-02D-1a', 0, 'pass')
                    if self.maturity < 1:
                        self.maturity = 1
                    preferance_reason.append('open format')
                    subject_area.append('General')
                    data_file_output.is_preferred_format = True
                # generic text/xml/json file check

                if 'html' not in mimetype and re.search(text_format_regex, mimetype):
                    self.setEvaluationCriteriumScore('FsF-R1.3-02D-1a', 0, 'pass')
                    self.setEvaluationCriteriumScore('FsF-R1.3-02D-1b', 0, 'pass')
                    self.setEvaluationCriteriumScore('FsF-R1.3-02D-1c', 0, 'fail')
                    self.maturity = 2
                    preferance_reason.extend(['long term format', 'open format', 'generic science format'])
                    subject_area.append('General')
                    data_file_output.is_preferred_format = True
                if 'html' in mimetype:
                    preferance_reason = []

                if preferance_reason:
                    preferred_detected = True

                data_file_output.mime_type = mimetype
                data_file_output.file_uri = url
                data_file_output.preference_reason = list(set(preferance_reason))
                data_file_output.subject_areas = list(set(subject_area))
                data_file_list.append(data_file_output)
            if preferred_detected:
                self.score.earned = 1
                self.setEvaluationCriteriumScore('FsF-R1.3-02D-1', 1, 'pass')
                #self.maturity = 3
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    'FsF-R1.3-02D : Could identify a file format commonly used by the scientific community -:' +
                    str(mimetype))
                self.result.test_status = 'pass'
        else:
            self.logger.warning(
                'FsF-R1.3-02D : Could not perform file format checks as data content identifier(s) unavailable/inaccesible'
            )
            self.result.test_status = 'fail'

        self.output = data_file_list
        self.result.output = self.output
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.score = self.score
