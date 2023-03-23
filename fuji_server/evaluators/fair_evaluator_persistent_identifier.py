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
    pids_which_resolve = {}

    def evaluate(self):
        self.result = Persistence(id=self.metric_number,
                                  metric_identifier=self.metric_identifier,
                                  metric_name=self.metric_name)
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.logger.info('FsF-F1-02D : PID schemes-based assessment supported by the assessment service - {}'.format(
            Mapper.VALID_PIDS.value))
        check_url = None
        identifiers_to_test = []
        # if PID found in unique identifier test..

        verified_pids = []
        verified_pid_schemes = []
        for pid, pid_info in self.fuji.pid_collector.items():
            if pid_info.get('verified') or not self.fuji.verify_pids:
                verified_pids.append(pid)
                verified_pid_schemes.append(pid_info.get('scheme'))
                if pid_info.get('resolved_url'):
                    self.fuji.isLandingPageAccessible = True
            else:
                self.logger.info('FsF-F1-02D : Found PID which could not be verified (does not resolve properly) -: '+str(pid))

        if verified_pids:
            self.output.resolved_url = self.fuji.landing_url
            self.output.resolvable_status = self.fuji.isLandingPageAccessible
            self.output.pid_scheme = str(verified_pid_schemes)
            self.output.pid = str(verified_pids)
            self.setEvaluationCriteriumScore('FsF-F1-02D-1', 0.5, 'pass')
            self.score.earned = 0.5
            self.maturity = 1
            if self.fuji.isLandingPageAccessible:
                self.setEvaluationCriteriumScore('FsF-F1-02D-2', 0.5, 'pass')
                self.maturity = 3
                self.result.test_status = 'pass'
                self.score.earned = self.total_score  # idenfier should be based on a persistence scheme and resolvable
            self.logger.log(self.fuji.LOG_SUCCESS,
                            'FsF-F1-02D : Persistence identifier scheme -: {}'.format(self.fuji.pid_scheme))
        else:
            self.score.earned = 0
            self.logger.warning('FsF-F1-02D : Could not identify a valid peristent identifier based on scheme and resolution')

        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output



