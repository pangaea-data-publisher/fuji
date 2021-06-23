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
from fuji_server.models.core_metadata_output import CoreMetadataOutput
from fuji_server.models.core_metadata import CoreMetadata
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_mapper import Mapper

class FAIREvaluatorCoreMetadata(FAIREvaluator):

    def evaluate(self):
        if self.fuji.landing_url is None:
            self.logger.warning('FsF-F2-01M : Metadata checks probably unreliable: landing page URL could not be determined')

        self.fuji.retrieve_metadata(self.fuji.extruct_result)
        self.result = CoreMetadata(id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name)

        metadata_required = Mapper.REQUIRED_CORE_METADATA.value
        metadata_found = {k: v for k, v in self.fuji.metadata_merged.items() if k in metadata_required}

        # this list is following the recommendation of  DataCite see: Fenner et al 2019 and Starr & Gastl, 2011
        partial_elements = ['creator', 'title', 'object_identifier', 'publication_date','publisher','object_type']
        # TODO: check the number of metadata elements which metadata_found has in common with metadata_required
        # set(a) & set(b)
        self.logger.info('FsF-F2-01M : Testing for required core descriptive metadata elements -: {}'.format(metadata_required))


        if set(metadata_found) == set(metadata_required):
            self.logger.log(self.fuji.LOG_SUCCESS,'FsF-F2-01M : Found required core descriptive metadata elements -: {}'.format(metadata_required))
            metadata_status = 'all metadata'
            self.maturity = 3
            self.score.earned = self.total_score
            self.setEvaluationCriteriumScore('FsF-F2-01M-3', 1, 'pass')
            self.setEvaluationCriteriumScore('FsF-F2-01M-2', 0.5, 'pass')
            test_status = 'pass'
        else:
            core_missing = list(set(metadata_required) - set(metadata_found))
            self.logger.warning('FsF-F2-01M : Not all required core descriptive metadata elements exist, missing -: {}'.format(str(core_missing)))
            self.logger.info('FsF-F2-01M : Testing for required core citation metadata elements -: {}'.format(partial_elements))
            if set(partial_elements).issubset(metadata_found):
                self.logger.log(self.fuji.LOG_SUCCESS,'FsF-F2-01M : Found required core citation metadata elements -: {}'.format(partial_elements))
                metadata_status = 'partial metadata'
                self.maturity = 2
                self.setEvaluationCriteriumScore('FsF-F2-01M-2', 0.5, 'pass')
                self.score.earned = self.total_score - 1
                test_status = 'pass'
            else:
                if len(metadata_found) >=2:
                    self.logger.info('FsF-F2-01M : Found some descriptive metadata elements -: ' + str(metadata_found.keys()))
                    metadata_status = 'some metadata'
                    self.maturity = 1
                    self.setEvaluationCriteriumScore('FsF-F2-01M-1', 0.5, 'pass')
                    self.score.earned = 0.5
                    test_status = 'pass'
                else:
                    metadata_status = 'insufficient metadata'  # status should follow enumeration in yaml
                    self.score.earned = 0
                    test_status = 'fail'
                partial_missing = list(set(partial_elements) - set(metadata_found))
                self.logger.warning('FsF-F2-01M : Not all required citation metadata elements exist, missing -: '+str(partial_missing))


        self.output = CoreMetadataOutput(core_metadata_status=metadata_status,
                                                     core_metadata_source=self.fuji.metadata_sources)
        #meta_output: CoreMetadataOutput = CoreMetadataOutput(core_metadata_status=metadata_status,
        #                                                     core_metadata_source=self.metadata_sources)
        self.output.core_metadata_found = metadata_found
        source_mechanisms = dict((y, x) for x, y in self.fuji.metadata_sources)
        for source_mechanism in source_mechanisms:
            if source_mechanism == 'embedded':
                self.setEvaluationCriteriumScore('FsF-F2-01M-1a', 0,'pass')
                self.setEvaluationCriteriumScore('FsF-F2-01M-1', 0.5, 'pass')
            if source_mechanism == 'negotiated':
                self.setEvaluationCriteriumScore('FsF-F2-01M-1b', 0,'pass')
                self.setEvaluationCriteriumScore('FsF-F2-01M-1', 0.5, 'pass')
            if source_mechanism == 'linked':
                self.setEvaluationCriteriumScore('FsF-F2-01M-1c', 0,'pass')
                self.setEvaluationCriteriumScore('FsF-F2-01M-1', 0.5, 'pass')
            if source_mechanism == 'signposting':
                self.setEvaluationCriteriumScore('FsF-F2-01M-1d', 0,'pass')
                self.setEvaluationCriteriumScore('FsF-F2-01M-1', 0.5, 'pass')
        self.result.test_status = test_status
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.output = self.output

