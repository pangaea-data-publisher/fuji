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
import requests
from tldextract import extract

from fuji_server import Persistence, PersistenceOutput
from fuji_server.models.persistence_output_inner import PersistenceOutputInner
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup

class FAIREvaluatorPersistentIdentifier(FAIREvaluator):
    """
    A class to evaluate that the data is assigned a persistent identifier (F1-02D). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the data is specified based on a commonly accepted persistent identifier scheme or
        the identifier is web-accesible, i.e., it resolves to a landing page with metadata of the data object.
    """


    def __init__(self, fuji_instance):
        self.pids_which_resolve = {}
        FAIREvaluator.__init__(self, fuji_instance)
        if self.fuji.metric_helper.get_metric_version() <= 0.5:
            metric = 'FsF-F1-02D'
        else:
            metric = 'FsF-F1-02M'
        self.set_metric(metric)

    def setPidsOutput(self):
        self.output.persistent_identifiers = []
        for pid, pid_info in self.fuji.pid_collector.items():
            if pid_info.get('is_persistent'):
                output_inner = PersistenceOutputInner()
                output_inner.pid = pid_info.get('pid')
                output_inner.pid_scheme = pid_info.get('scheme')
                if pid_info.get('resolved_url'):
                    output_inner.resolvable_status = True
                output_inner.resolved_url = pid_info.get('resolved_url')
                self.output.persistent_identifiers.append(output_inner)

    def testCompliesWithPIDScheme(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-1'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-1')
            for pid, pid_info in self.fuji.pid_collector.items():
                if pid_info.get('is_persistent'):
                    test_status = True
            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + '-1', test_score, 'pass')
                self.score.earned = test_score
                self.maturity = self.metric_tests.get(self.metric_identifier + '-1').metric_test_maturity_config
                test_status = True
        return test_status

    def testIfLandingPageResolves(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-2'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-2')
            for pid, pid_info in self.fuji.pid_collector.items():
                if pid_info.get('verified') or not self.fuji.verify_pids:
                    if pid_info.get('resolved_url'):
                        self.fuji.isLandingPageAccessible = True
                        self.logger.info(self.metric_identifier + ' : Found PID which could be verified (does resolve properly) -: ' + str(pid))
                    else:
                        self.logger.info(
                            self.metric_identifier + ' : Found PID which could not be verified (does not resolve properly) -: ' + str(
                                pid))
            if self.fuji.isLandingPageAccessible:
                test_status = True
                self.setEvaluationCriteriumScore(self.metric_identifier + '-2', test_score, 'pass')
                self.maturity = self.metric_tests.get(self.metric_identifier + '-2').metric_test_maturity_config
                self.score.earned = self.total_score  # idenfier should be based on a persistence scheme and resolvable
            self.logger.log(self.fuji.LOG_SUCCESS,
                            self.metric_identifier + ' : Persistence identifier scheme -: {}'.format(self.fuji.pid_scheme))
        return test_status


    def evaluate(self):
        self.result = Persistence(id=self.metric_number,
                                  metric_identifier=self.metric_identifier,
                                  metric_name=self.metric_name)
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.logger.info(self.metric_identifier + ' : PID schemes-based assessment supported by the assessment service - {}'.format(
            Mapper.VALID_PIDS.value))

        self.result.test_status = 'fail'
        self.setPidsOutput()
        if self.testCompliesWithPIDScheme():
            self.result.test_status = 'pass'
        if self.testIfLandingPageResolves():
            self.result.test_status = 'pass'

        '''else:
            self.score.earned = 0
            self.logger.warning(self.metric_identifier + ' : Could not identify a valid peristent identifier based on scheme and resolution')'''



        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output



