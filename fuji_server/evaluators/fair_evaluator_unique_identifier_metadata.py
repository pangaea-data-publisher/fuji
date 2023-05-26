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
import uuid
import idutils
import hashid
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.models.uniqueness_output import UniquenessOutput
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.evaluators.fair_evaluator import FAIREvaluator


class FAIREvaluatorUniqueIdentifierMetadata(FAIREvaluator):
    """
    A class to evaluate the globally unique identifier of the data (F1-01D). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the data is assigned to a unique identifier (UUID/HASH) that folows a proper syntax or
        identifier is resolvable and follows a defined unique identifier syntax (URL, IRI).
    """
    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        if self.fuji.metric_helper.get_metric_version() <= 0.5:
            metric = 'FsF-F1-01D'
        else:
            metric = 'FsF-F1-01M'
            #after 0.5 seperate metrics for metadata and data
        self.set_metric(metric, metrics=fuji_instance.METRICS)

    def testCompliesWithIdutilsScheme(self, validschemes = []):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-1'):
            self.logger.info(self.metric_identifier+' : Using idutils schemes to identify unique or persistent identifiers for metadata')
            idhelper = IdentifierHelper(self.fuji.id)
            found_ids = idhelper.identifier_schemes
            self.logger.info(self.metric_identifier+' :Starting assessment on identifier: {}'.format(self.fuji.id))
            if len(found_ids) > 0:
                self.logger.log(self.fuji.LOG_SUCCESS, self.metric_identifier+' : Unique identifier schemes found {}'.format(found_ids))
                self.setEvaluationCriteriumScore('FsF-F1-01D-1', self.total_score, 'pass')
                self.maturity = self.metric_tests.get(self.metric_identifier + '-1').metric_test_maturity_config
                self.output.guid = self.fuji.id
                self.score.earned = self.total_score
                found_id = idhelper.preferred_schema
                self.fuji.id_scheme = idhelper.identifier_schemes[0]
                if idhelper.is_persistent:
                    self.fuji.pid_scheme = found_id
                    self.fuji.pid_url = idhelper.identifier_url
                self.logger.info(self.metric_identifier + ' : Finalized unique identifier scheme - {}'.format(found_id))
                self.output.guid_scheme = found_id
                test_status = True
        return test_status

    def testCompliesWithUUIDorHASH(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-2'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-2')
            if self.verify_uuid(self.fuji.id):
                self.logger.log(self.fuji.LOG_SUCCESS, self.metric_identifier + ' : Unique identifier (UUID) scheme found')
                self.output.guid_scheme = 'uuid'
                test_status = True
            elif self.verify_hash(self.fuji.id):
                self.output.guid_scheme = 'hash'
                self.logger.log(self.fuji.LOG_SUCCESS, self.metric_identifier + ' : Unique identifier (SHA,MD5) scheme found')
                test_status = True
            if test_status:
                self.setEvaluationCriteriumScore(self.metric_identifier + '-2', test_score, 'pass')
                self.output.guid = self.fuji.id
                self.maturity =  self.maturity = self.metric_tests.get(self.metric_identifier + '-2').metric_test_maturity_config
                self.score.earned = test_score
        return test_status

    def evaluate(self):
        # ======= CHECK IDENTIFIER UNIQUENESS =======
        if self.metric_identifier in self.metrics:
            self.result = Uniqueness(id=self.metric_number,
                                     metric_identifier=self.metric_identifier,
                                     metric_name=self.metric_name)
            self.output = UniquenessOutput()
            self.result.test_status = 'fail'
            if self.testCompliesWithUUIDorHASH():
                self.result.test_status = 'pass'
            if self.testCompliesWithIdutilsScheme():
                self.result.test_status = 'pass'
            else:
                self.result.test_status = 'fail'
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + ' : Failed to check the identifier scheme!.')
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity

    def verify_uuid(self, id):
        try:
            uuid_version = uuid.UUID(id).version
            if uuid_version is not None:
                return True
            else:
                return False
        except ValueError:
            return False

    def verify_hash(self, id):
        try:
            hash = hashid.HashID()
            validhash = False
            for hashtype in hash.identifyHash(id):
                if re.search(r'^(sha|md5|blake)', hashtype.name, re.IGNORECASE):
                    validhash = True
            return validhash
        except Exception:
            return False
