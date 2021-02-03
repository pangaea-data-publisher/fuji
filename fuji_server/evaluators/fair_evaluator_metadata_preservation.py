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
from fuji_server.models.metadata_preserved import MetadataPreserved
from fuji_server.models.metadata_preserved_output import MetadataPreservedOutput


class FAIREvaluatorMetadataPreserved(FAIREvaluator):
    def evaluate(self):
        registry_bound_pid = ['doi']
        self.result = MetadataPreserved(id=self.fuji.count, metric_identifier=self.metric_identifier,
                                                metric_name=self.metric_name)
        outputs = []
        test_status = 'fail'
        score = 0
        if self.fuji.pid_scheme:
            if self.fuji.pid_scheme in registry_bound_pid:
                test_status = 'pass'
                outputs.append(MetadataPreservedOutput(metadata_preservation_method='datacite'))
                score = 1
                self.setEvaluationCriteriumScore('FsF-A2-01M-1', 1, 'pass')
                self.logger.log(self.fuji.LOG_SUCCESS,
                    '{0} : Metadata registry bound PID system used: ' + self.fuji.pid_scheme.format(self.metric_identifier))
            else:
                self.logger.warning(
                    '{0} : NO metadata registry bound PID system used'.format(self.metric_identifier))
        self.score.earned = score
        self.result.score = self.score
        self.result.output = outputs
        self.result.metric_tests = self.metric_tests
        self.result.test_status = test_status