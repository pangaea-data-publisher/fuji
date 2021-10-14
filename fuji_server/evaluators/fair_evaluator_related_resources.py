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
#from fuji_server.models.related_resource_output_inner import RelatedResourceOutputInner


class FAIREvaluatorRelatedResources(FAIREvaluator):

    def evaluate(self):
        self.result = RelatedResource(id=self.metric_number,
                                      metric_identifier=self.metric_identifier,
                                      metric_name=self.metric_name)
        self.output = RelatedResourceOutput()

        self.logger.info('{0} : Total number of related resources extracted -: {1}'.format(
            self.metric_identifier, len(self.fuji.related_resources)))

        # if self.metadata_merged.get('related_resources'):
        pid_used = False
        if self.fuji.related_resources:
            #print(self.fuji.related_resources)
            # QC check: exclude potential incorrect relation
            self.fuji.related_resources = [
                item for item in self.fuji.related_resources if item.get('related_resource') != self.fuji.pid_url
            ]

            self.logger.log(
                self.fuji.LOG_SUCCESS,
                '{0} : Number of related resources after QC step -: {1}'.format(self.metric_identifier,
                                                                                len(self.fuji.related_resources)))

        if self.fuji.related_resources:  # TODO include source of relation
            for relation in self.fuji.related_resources:
                relation_identifier = IdentifierHelper(relation.get('related_resource'))
                if relation_identifier.is_persistent or 'url' in relation_identifier.identifier_schemes:
                    pid_used = True
            self.output = self.fuji.related_resources
            self.result.test_status = 'pass'
            self.setEvaluationCriteriumScore('FsF-I3-01M-1', 1, 'pass')
            self.score.earned = self.total_score
            self.maturity = 2
            if pid_used:
                self.setEvaluationCriteriumScore('FsF-I3-01M-2', 1, 'pass')
                self.maturity = 3
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.score = self.score
        self.result.output = self.output
