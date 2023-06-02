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
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.models.related_resource import RelatedResource
from fuji_server.models.related_resource_output import RelatedResourceOutput


class FAIREvaluatorRelatedResources(FAIREvaluator):
    """
    A class to evaluate that the metadata links between the data and its related entities (I3-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate the links between metadata whether they relate explicitly in metadata and
        they relate by machine-readable links/identifier.
    """
    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric('FsF-I3-01M')
        self.pid_used = False

    def testRelatedResourcesAvailable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-1'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-1')
        for relation in self.fuji.related_resources:
            if isinstance(relation.get('related_resource'), list):
                relation['related_resource'] = relation.get('related_resource')[0]
            relation_identifier = IdentifierHelper(relation.get('related_resource'))
            if relation_identifier.is_persistent or 'url' in relation_identifier.identifier_schemes:
                self.pid_used = True
        self.output = self.fuji.related_resources
        self.setEvaluationCriteriumScore(self.metric_identifier + '-1', test_score, 'pass')
        self.score.earned = self.total_score
        self.maturity = self.getTestConfigMaturity(self.metric_identifier + '-1')
        return test_status

    def testRelatedResourcesMachineReadable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-2'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-2')
            if self.pid_used:
                test_status = True
                self.score.earned = self.total_score
                self.setEvaluationCriteriumScore(self.metric_identifier + '-1', test_score, 'pass')
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + '-2')
        return test_status

    def evaluate(self):
        self.result = RelatedResource(id=self.metric_number,
                                      metric_identifier=self.metric_identifier,
                                      metric_name=self.metric_name)
        self.output = RelatedResourceOutput()

        self.logger.info('{0} : Total number of related resources extracted -: {1}'.format(
            self.metric_identifier, len(self.fuji.related_resources)))

        # if self.metadata_merged.get('related_resources'):
        related_status = 'fail'
        if self.testRelatedResourcesAvailable():
            related_status = 'pass'
            self.testRelatedResourcesMachineReadable()
        self.result.metric_tests = self.metric_tests
        self.result.test_status = related_status
        self.result.maturity = self.maturity
        self.result.score = self.score
        self.result.output = self.output
