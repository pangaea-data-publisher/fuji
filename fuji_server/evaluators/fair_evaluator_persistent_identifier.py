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

    def check_if_pid_resolves(self, candidate_pid):
        if candidate_pid not in self.pids_which_resolve:
            try:
                requestHelper = RequestHelper(candidate_pid, self.logger)
                requestHelper.setAcceptType(AcceptTypes.default)  # request
                requestHelper.content_negotiate('FsF-F1-02D', ignore_html=False)

                if requestHelper.response_content:
                    self.pids_which_resolve[candidate_pid] = requestHelper.redirect_url
                    return requestHelper.redirect_url
                else:
                    return None
            except Exception as e:
                print('PID resolve test error',e)
                return None
        else:
            return self.pids_which_resolve.get(candidate_pid)
    # check if PID resolves to (known) landing page
    def pid_resolves_to_landing_page(self, candidate_pid):
        candidate_landing_url = self.check_if_pid_resolves(candidate_pid)
        if candidate_landing_url and self.fuji.landing_url:
            candidate_landing_url_parts = extract(candidate_landing_url)
            landing_url_parts = extract(self.fuji.landing_url)
            input_id_domain = candidate_landing_url_parts.domain + '.' + candidate_landing_url_parts.suffix
            landing_domain = landing_url_parts.domain + '.' + landing_url_parts.suffix
            if landing_domain != input_id_domain:
                self.logger.warning(
                    'FsF-F1-02D : Landing page domain resolved from PID found in metadata does not match with input URL domain'
                )
                self.logger.warning(
                    'FsF-F2-01M : Seems to be a catalogue entry or alternative representation of the data set, landing page URL domain resolved from PID found in metadata does not match with input URL domain'
                )
                return False
            else:
                self.logger.info(
                    'FsF-F1-02D : Verified PID found in metadata since it is resolving to user input URL domain'
                )
                return True
        else:
            return False

    def evaluate(self):
        self.result = Persistence(id=self.metric_number,
                                  metric_identifier=self.metric_identifier,
                                  metric_name=self.metric_name)
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.logger.info('FsF-F1-02D : PID schemes-based assessment supported by the assessment service - {}'.format(
            Mapper.VALID_PIDS.value))
        check_url = None
        identifiers_to_test = None
        # if PID found in unique identifier test..
        if self.fuji.pid_scheme:
            identifiers_to_test = [self.fuji.pid_url]
        else:
            identifiers_to_test = [self.fuji.id]
        if self.fuji.metadata_merged.get('object_identifier'):
            if isinstance(self.fuji.metadata_merged.get('object_identifier'), list):
                identifiers_to_test.extend(self.fuji.metadata_merged.get('object_identifier'))
            else:
                identifiers_to_test.append(self.fuji.metadata_merged.get('object_identifier'))
        identifiers_to_test = list(set(identifiers_to_test))

        verified_pids = []
        verified_pid_schemes = []
        if identifiers_to_test:
            for test_pid in identifiers_to_test:
                idhelper = IdentifierHelper(test_pid)
                if idhelper.is_persistent:
                    if test_pid != self.fuji.id:
                        if self.pid_resolves_to_landing_page(test_pid):
                            verified_pids.append(test_pid)
                            verified_pid_schemes.append(idhelper.preferred_schema)
                    else:
                        verified_pids.append(test_pid)
                        verified_pid_schemes.append(idhelper.preferred_schema)

            if self.fuji.landing_url:
                self.output.resolved_url = self.fuji.landing_url  # url is active, although the identifier is not based on a pid scheme
                self.output.resolvable_status = True
                self.logger.info('FsF-F1-02D : Object identifier active (status code = 200)')
                self.fuji.isMetadataAccessible = True

        if verified_pids:
            self.output.pid_scheme = str(verified_pid_schemes)
            self.output.pid = str(verified_pids)
            self.setEvaluationCriteriumScore('FsF-F1-02D-1', 0.5, 'pass')
            self.score.earned = 0.5
            self.maturity = 1
            if self.fuji.isMetadataAccessible:
                self.setEvaluationCriteriumScore('FsF-F1-02D-2', 0.5, 'pass')
                self.maturity = 3
                self.result.test_status = 'pass'
                self.score.earned = self.total_score  # idenfier should be based on a persistence scheme and resolvable
            self.logger.log(self.fuji.LOG_SUCCESS,
                            'FsF-F1-02D : Persistence identifier scheme -: {}'.format(self.fuji.pid_scheme))
        else:
            self.score.earned = 0
            self.logger.warning('FsF-F1-02D : Not a persistent identifier scheme -: {}'.format(self.fuji.id_scheme))

        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output



