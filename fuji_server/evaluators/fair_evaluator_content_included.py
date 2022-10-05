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
import socket

import requests

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.identifier_included import IdentifierIncluded
from fuji_server.models.identifier_included_output import IdentifierIncludedOutput
from fuji_server.models.identifier_included_output_inner import IdentifierIncludedOutputInner
import urllib


class FAIREvaluatorContentIncluded(FAIREvaluator):
    """
    A class to evaluate whether the metadata includes the identifier of the data is being described (F3-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the metadata contains an identifier, e.g., PID or URL, which indicates the location of the downloadable data content or
        a data identifier that matches the identifier as part of the assessment request.
    """

    def evaluate(self):
        socket.setdefaulttimeout(1)

        self.result = IdentifierIncluded(id=self.metric_number,
                                         metric_identifier=self.metric_identifier,
                                         metric_name=self.metric_name)
        self.output = IdentifierIncludedOutput()

        #id_object = self.fuji.metadata_merged.get('object_identifier')
        #self.output.object_identifier_included = id_object
        contents = self.fuji.metadata_merged.get('object_content_identifier')
        #if id_object is not None:
        #    self.logger.info('FsF-F3-01M : Object identifier specified -: {}'.format(id_object))
        score = 0
        content_list = []
        if contents:
            #print(contents)
            if isinstance(contents, dict):
                contents = [contents]
            #ignore empty?
            contents = [c for c in contents if c]
            #keep unique only -
            #contents = list({cv['url']:cv for cv in contents}.values())
            #print(contents)
            number_of_contents = len(contents)

            self.logger.log(self.fuji.LOG_SUCCESS,
                            'FsF-F3-01M : Number of object content identifier found -: {}'.format(number_of_contents))
            self.maturity = 1
            score = 0.5
            self.setEvaluationCriteriumScore('FsF-F3-01M-1', 0.5, 'pass')
            if number_of_contents >= self.fuji.FILES_LIMIT:
                self.logger.info(
                    'FsF-F3-01M : The total number of object (content) identifiers specified is above threshold, will use the first -: {} content identifiers for the tests'
                    .format(self.fuji.FILES_LIMIT))
                contents = contents[:self.fuji.FILES_LIMIT]

            for content_link in contents:
                # self.logger.info('FsF-F3-01M : Object content identifier included {}'.format(content_link.get('url')))
                did_output_content = IdentifierIncludedOutputInner()
                did_output_content.content_identifier_included = content_link

                if content_link.get('url'):
                    content_list.append(did_output_content)
                    self.fuji.content_identifier.append(content_link)
                else:
                    self.logger.warning('FsF-F3-01M : Object (content) url is empty -: {}'.format(content_link))

        else:
            self.logger.warning('FsF-F3-01M : Data (content) identifier is missing.')

        if content_list:
            self.maturity = 3
            score = 1
            self.setEvaluationCriteriumScore('FsF-F3-01M-1', 0.5, 'pass')
            self.setEvaluationCriteriumScore('FsF-F3-01M-2', 0.5, 'pass')
        self.score.earned = score
        if score > 0.5:
            self.result.test_status = 'pass'
        self.result.metric_tests = self.metric_tests
        self.output.object_content_identifier_included = content_list
        self.result.output = self.output
        self.result.maturity = self.maturity
        self.result.score = self.score
