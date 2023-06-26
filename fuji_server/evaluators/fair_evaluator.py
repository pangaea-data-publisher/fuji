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
import re

from fuji_server.models.fair_result_common_score import FAIRResultCommonScore
from fuji_server.models.fair_result_evaluation_criterium import FAIRResultEvaluationCriterium
from fuji_server.helper.metadata_mapper import Mapper


class FAIREvaluator:
    """
    A super class of all the FUJI evaluators.

    ...
    Attributes
    ----------
    maturity_levels : dict
        A dictionary showing the maturity level, {0: 'incomplete', 1: 'initial', 2: 'moderate', 3: 'advanced'}
    fuji : Fuji
        A fuji instance object
    metric_identifier : str
        The identifier of FAIR FUJI implementation
    metrics : str
        FUJI metrics
    result : Result
        Result that contains score, output, metric tests, test status, and maturity of each evaluator
    maturity : int
        Maturity level of each evaluator
    isDebug : bool
        Boolean to enable debugging process
    logger : logging.Logger
        Logger to log during the evaluation process
    """

    #according to the CMMI model
    maturity_levels = Mapper.MATURITY_LEVELS.value
    #{0: 'incomplete', 1: 'initial', 2: 'managed', 3: 'defined', 4: 'quantitatively managed',5: 'optimizing'}
    def __init__(self, fuji_instance):
        """
        Parameters
        ----------
        fuji_instance:Fuji
            Fuji instance
        """
        self.fuji = fuji_instance
        self.metric_identifier = None
        self.metrics = None
        self.metric_number = None
        self.metric_name = None
        self.result = None
        self.maturity = 0
        self.metric_tests = dict()
        self.isDebug = self.fuji.isDebug
        self.fuji.count = self.fuji.count + 1
        self.logger = self.fuji.logger
        self.metric_regex = r'FsF-[FAIR][0-9]?(\.[0-9])?-[0-9]+[MD]+(-[0-9]+[a-z]?)?'


    def set_metric(self, metric_identifier):
        """Set the metric for evaluation process.

        Parameters
        ----------
        metric_identifier:str
            The metric identifier
        metrics: str
            FUJI metrics
        """
        self.metrics = self.fuji.METRICS
        self.metric_identifier = metric_identifier
        if self.metric_identifier is not None and self.metric_identifier in self.metrics:
            self.agnostic_identifier = self.metrics.get(metric_identifier).get('agnostic_identifier')
            self.community_identifier = self.metrics.get(metric_identifier).get('metric_identifier')
            self.total_score = int(self.metrics.get(metric_identifier).get('total_score'))
            self.score = FAIRResultCommonScore(total=self.total_score)
            self.metric_name = self.metrics.get(metric_identifier).get('metric_name')
            self.metric_number = self.metrics.get(metric_identifier).get('metric_number')
            self.initializeEvaluationCriteria()

    def evaluate(self):
        """To be implemented (override) in the child class"""
        #Do the main FAIR check here
        return True

    def getResult(self):
        """Get result of evaluation and pack it into dictionary."""
        if self.metric_identifier in self.metrics:
            self.evaluate()

        if self.result:
            self.result.metric_identifier = self.metrics.get(self.result.metric_identifier).get('metric_identifier')
            return self.result.to_dict()
        else:
            return {}


    def isTestDefined(self, testid):
        if testid  in self.metric_tests:
            return True
        else:
            self.logger.warning(
                self.metric_identifier+' : This test is not defined in the metric YAML -: '+ str(testid))
            return False

    def initializeEvaluationCriteria(self):
        """Initialize the evaluation criteria."""
        all_metric_tests = self.metrics.get(self.metric_identifier).get('metric_tests')
        if all_metric_tests is not None:
            for metric_test in all_metric_tests:
                evaluation_criterium = FAIRResultEvaluationCriterium()
                #evaluation_criterium.metric_test_identifier = metric_test.get('metric_test_identifier')
                evaluation_criterium.metric_test_status = 'fail'
                evaluation_criterium.metric_test_name = metric_test.get('metric_test_name')
                evaluation_criterium.metric_test_score = 0
                evaluation_criterium.metric_test_score_config = metric_test.get('metric_test_score')
                evaluation_criterium.metric_test_maturity = None
                evaluation_criterium.metric_test_maturity_config = metric_test.get('metric_test_maturity')
                evaluation_criterium.metric_test_config = metric_test.get('metric_test_config')
                if metric_test.get('agnostic_test_identifier'):
                    self.metric_tests[metric_test.get('agnostic_test_identifier')] = evaluation_criterium

    def setEvaluationCriteriumScore(self,
                                    criterium_id,
                                    metric_test_score=0,
                                    metric_test_status='fail',
                                    metric_test_maturity=None):
        """Set the evaluation criterium score of each evaluator.

        Parameters
        ----------
        criterium_id : str
            The metric identifier
        metric_test_score : float, optional
            the default is 0
        metric_test_status : str, optional
            the default is 'fail'
        metric_test_maturity : int, optional
        """
        evaluation_criterium = self.metric_tests.get(criterium_id)
        if evaluation_criterium is not None:
            if metric_test_score != evaluation_criterium.metric_test_score_config:
                evaluation_criterium.metric_test_score = metric_test_score
            else:
                if metric_test_status == 'pass':
                    evaluation_criterium.metric_test_score = evaluation_criterium.metric_test_score_config
            evaluation_criterium.metric_test_status = metric_test_status
            if metric_test_status == 'pass':
                evaluation_criterium.metric_test_maturity = evaluation_criterium.metric_test_maturity_config
            self.metric_tests[criterium_id] = evaluation_criterium

    def getTestConfigScore(self, criterium_id):
        if self.metric_tests.get(criterium_id):
             return self.metric_tests[criterium_id].metric_test_score_config
        else:
            return False

    def getTestConfigMaturity(self, criterium_id):
        #get the configured maturity from YAML
        if self.metric_tests.get(criterium_id):
            return self.metric_tests[criterium_id].metric_test_maturity_config
        else:
            return False

