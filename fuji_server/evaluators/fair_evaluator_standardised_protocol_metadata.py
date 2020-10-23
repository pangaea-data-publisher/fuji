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
from typing import List, Any

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.standardised_protocol_metadata import StandardisedProtocolMetadata
from fuji_server.models.standardised_protocol_metadata_output import StandardisedProtocolMetadataOutput
from fuji_server.helper.metadata_mapper import Mapper
from urllib.parse import urlparse

class FAIREvaluatorStandardisedProtocolMetadata(FAIREvaluator):
    def evaluate(self):

        self.result = StandardisedProtocolMetadata(id=self.fuji.count, metric_identifier=self.metric_identifier,
                                               metric_name=self.metric_name)
        metadata_output = data_output = None
        metadata_required = Mapper.REQUIRED_CORE_METADATA.value
        metadata_found = {k: v for k, v in self.fuji.metadata_merged.items() if k in metadata_required}
        test_status = 'fail'
        score = 0

        if self.fuji.landing_url is not None:
            # parse the URL and return the protocol which has to be one of Internet RFC on Relative Uniform Resource Locators
            metadata_parsed_url = urlparse(self.fuji.landing_url)
            metadata_url_scheme = metadata_parsed_url.scheme

            if metadata_url_scheme in self.fuji.STANDARD_PROTOCOLS:
                metadata_output = {metadata_url_scheme: self.fuji.STANDARD_PROTOCOLS.get(metadata_url_scheme)}
                test_status = 'pass'
                score += 1
            if set(metadata_found) != set(metadata_required):
                self.logger.info(
                    '{0} : NOT all required metadata given, see: FsF-F2-01M'.format(self.metric_identifier))
                # parse the URL and return the protocol which has to be one of Internet RFC on Relative Uniform Resource Locators
        else:
            self.logger.info(
                '{0} : Metadata Identifier is not actionable or protocol errors occured'.format(self.metric_identifier))

        self.score.earned = score
        self.result.score = self.score
        self.result.output = StandardisedProtocolMetadataOutput(standard_metadata_protocol= metadata_output)
        self.result.test_status = test_status