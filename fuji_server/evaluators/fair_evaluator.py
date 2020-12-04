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
import logging
from typing import List, Dict
from fuji_server.models.fair_result_common_score import FAIRResultCommonScore
from fuji_server.models.fair_result_evaluation_criterium import FAIRResultEvaluationCriterium
from pprint import pprint


from fuji_server.helper.log_message_filter import MessageFilter

class FAIREvaluator:
    def __init__(self, fuji_instance):
        self.fuji=fuji_instance
        self.metric_identifier = None
        self.metrics = None
        self.result = None
        self.metric_tests = dict()
        self.isDebug=self.fuji.isDebug
        self.fuji.count = self.fuji.count+1
        self.logger = self.fuji.logger
        if self.isDebug == True:
            self.msg_filter = MessageFilter()
            self.logger.addFilter(self.msg_filter)
            self.logger.setLevel(logging.INFO)  # set to debug in testing environment

    def set_metric(self, metric_identifier, metrics):
        self.metrics = metrics
        self.metric_identifier = metric_identifier
        if self.metric_identifier is not None:
            self.total_score = int(self.metrics.get(metric_identifier).get('total_score'))
            self.score = FAIRResultCommonScore(total=self.total_score)
            self.metric_name = self.metrics.get(metric_identifier).get('metric_name')
            self.initializeEvaluationCriteria()


    def evaluate(self):
        #Do the main FAIR check here
         return True

    def getResult(self):
        self.evaluate()
        return self.result.to_dict()

    def initializeEvaluationCriteria(self):
        all_metric_tests = self.metrics.get(self.metric_identifier).get('metric_tests')
        if all_metric_tests is not None:
            for metric_test in all_metric_tests:
                evaluation_criterium = FAIRResultEvaluationCriterium()
                #evaluation_criterium.metric_test_identifier = metric_test.get('metric_test_identifier')
                evaluation_criterium.metric_test_status = 'fail'
                evaluation_criterium.metric_test_name = metric_test.get('metric_test_name')
                evaluation_criterium.metric_test_score = 0
                self.metric_tests[metric_test.get('metric_test_identifier')] = evaluation_criterium

    def setEvaluationCriteriumScore(self, criterium_id, metric_test_score = 0, metric_test_status = 'fail'):
        evaluation_criterium = self.metric_tests.get(criterium_id)
        if evaluation_criterium is not None:
            evaluation_criterium.metric_test_score = metric_test_score
            evaluation_criterium.metric_test_status = metric_test_status
            self.metric_tests[criterium_id] = evaluation_criterium