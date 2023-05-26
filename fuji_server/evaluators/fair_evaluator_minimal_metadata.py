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
    """
    A class to evaluate the metadata that includes core descriptive elements (creator, title, data identifier, publisher, publication date, summary, and
    keywords) to support data finding (F2-01M). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate metadata whether it specifies the core metadata, e.g., creator, title, publication date, etc.,
        through appropriate metadata fields.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric('FsF-F2-01M', metrics=fuji_instance.METRICS)
        self.metadata_found = {}
        # this list is following the recommendation of  DataCite see: Fenner et al 2019 and Starr & Gastl, 2011
        self.partial_elements = ['creator', 'title', 'object_identifier', 'publication_date', 'publisher', 'object_type']

    def testMetadataCommonMethodsAvailable(self):
        #implements FsF-F2-01M-1
        if self.isTestDefined('FsF-F2-01M-1'):
            test_score = self.metric_tests.get('FsF-F2-01M-1').metric_test_score_config
            if len(self.metadata_found) >= 1:
                self.logger.info('FsF-F2-01M : Found some descriptive metadata elements -: ' +
                                 str(self.metadata_found.keys()))
                self.setEvaluationCriteriumScore('FsF-F2-01M-1', test_score, 'pass')
                source_mechanisms = dict((y, x) for x, y in list(set(self.fuji.metadata_sources)))
                for source_mechanism in source_mechanisms:
                    if source_mechanism == 'embedded':
                        self.setEvaluationCriteriumScore('FsF-F2-01M-1a', 0, 'pass')
                    if source_mechanism == 'negotiated':
                        self.setEvaluationCriteriumScore('FsF-F2-01M-1b', 0, 'pass')
                    if source_mechanism == 'linked':
                        self.setEvaluationCriteriumScore('FsF-F2-01M-1c', 0, 'pass')
                    if source_mechanism == 'signposting':
                        self.setEvaluationCriteriumScore('FsF-F2-01M-1d', 0, 'pass')
                self.maturity = self.metric_tests.get('FsF-F2-01M-1').metric_test_maturity_config
                self.score.earned = test_score
                partial_missing = list(set(self.partial_elements) - set(self.metadata_found))
                if partial_missing:
                    self.logger.warning(self.metric_identifier+' : Not all required citation metadata elements exist, missing -: ' +
                                        str(partial_missing))

            return True
        else:
            return False

    def testCoreDescriptiveMetadataAvailable(self):
        if self.isTestDefined('FsF-F2-01M-3'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-3')
            test_status = False
            if set(self.metadata_found) == set(Mapper.REQUIRED_CORE_METADATA.value):
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier+' : Found required core descriptive metadata elements -: {}'.format(Mapper.REQUIRED_CORE_METADATA.value))
                self.maturity = self.metric_tests.get('FsF-F2-01M-3').metric_test_maturity_config
                self.score.earned = self.total_score
                self.setEvaluationCriteriumScore('FsF-F2-01M-3', test_score, 'pass')
                test_status = True
            else:
                core_missing = list(set(Mapper.REQUIRED_CORE_METADATA.value) - set(self.metadata_found))
                self.logger.warning(
                    self.metric_identifier+' : Not all required core descriptive metadata elements exist, missing -: {}'.format(
                        str(core_missing)))
        return test_status


    def testCoreCitationMetadataAvailable(self):
        if self.isTestDefined('FsF-F2-01M-2'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-2')
            test_status = False
            if set(self.partial_elements).issubset(self.metadata_found):
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    self.metric_identifier+' : Found required core citation metadata elements -: {}'.format(self.partial_elements))
                self.maturity = self.metric_tests.get('FsF-F2-01M-2').metric_test_maturity_config
                self.setEvaluationCriteriumScore('FsF-F2-01M-2', test_score, 'pass')
                self.score.earned = self.score.earned + test_score
                test_status = True
        return test_status

    def evaluate(self):
        if self.fuji.landing_url is None:
            self.logger.warning(
                self.metric_identifier+' : Metadata checks probably unreliable: landing page URL could not be determined')
        self.result = CoreMetadata(id=self.metric_number,
                                   metric_identifier=self.metric_identifier,
                                   metric_name=self.metric_name)

        test_status = 'fail'
        metadata_status = 'insufficient metadata'
        self.metadata_found = {k: v for k, v in self.fuji.metadata_merged.items() if k in Mapper.REQUIRED_CORE_METADATA.value}
        self.logger.info(
            self.metric_identifier+' : Testing if any metadata has been made available via common web standards')
        if self.testMetadataCommonMethodsAvailable():
            test_status = 'pass'
            metadata_status = 'some metadata'
        self.logger.info(
            self.metric_identifier+' : Testing for required core citation metadata elements -: {}'.format(Mapper.REQUIRED_CORE_METADATA.value))
        if self.testCoreCitationMetadataAvailable():
            test_status = 'pass'
            metadata_status = 'partial metadata'
        self.logger.info(
            self.metric_identifier+' : Testing for required core descriptive metadata elements -: {}'.format(Mapper.REQUIRED_CORE_METADATA.value))
        if self.testCoreDescriptiveMetadataAvailable():
            test_status = 'pass'
            metadata_status = 'all metadata'
        print('METRIC ', self.metric_identifier)
        self.output = CoreMetadataOutput(core_metadata_status=metadata_status,
                                         core_metadata_source=list(set(self.fuji.metadata_sources)))

        self.output.core_metadata_found = self.metadata_found
        self.result.test_status = test_status
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.output = self.output
