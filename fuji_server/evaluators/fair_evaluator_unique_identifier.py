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
from fuji_server.helper.metadata_mapper import Mapper


class FAIREvaluatorUniqueIdentifier(FAIREvaluator):

    def evaluate(self):
        # ======= CHECK IDENTIFIER UNIQUENESS =======
        self.result = Uniqueness(id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = UniquenessOutput()
        schemes = [i[0] for i in idutils.PID_SCHEMES]
        self.logger.info('FsF-F1-01D : Using idutils schemes')
        idhelper = IdentifierHelper(self.fuji.id)
        found_ids = idhelper.identifier_schemes
        #found_ids = idutils.detect_identifier_schemes(self.fuji.id)  # some schemes like PMID are generic
        if len(found_ids) > 0:
            self.logger.log(self.fuji.LOG_SUCCESS,'FsF-F1-01D : Unique identifier schemes found {}'.format(found_ids))
            self.setEvaluationCriteriumScore('FsF-F1-01D-1',1, 'pass')
            self.output.guid = self.fuji.id
            self.score.earned = self.total_score
            self.maturity = 3
            # identify main scheme
            found_id = idhelper.preferred_schema
            self.fuji.id_scheme = idhelper.identifier_schemes[0]
            '''
            if len(found_ids) == 1:
                #self.fuji.pid_url = self.fuji.id
                self.fuji.id_scheme = found_ids[0]
                #self.fuji.id_scheme = 'url'
            else:
                if 'url' in found_ids:  # ['doi', 'url']
                    found_ids.remove('url')
                    #self.fuji.pid_url = self.fuji.id
                self.fuji.id_scheme = found_ids[0]
            found_id = found_ids[0]  # TODO: take the first element of list, e.g., [doi, handle]
            '''
            if idhelper.is_persistent:
                self.fuji.pid_scheme = found_id
                self.fuji.pid_url = idhelper.identifier_url
            self.logger.info('FsF-F1-01D : Finalized unique identifier scheme - {}'.format(found_id))
            self.output.guid_scheme = found_id
            self.result.test_status = 'pass'
        elif self.verify_uuid(self.fuji.id):
            self.logger.log(self.fuji.LOG_SUCCESS,'FsF-F1-01D : Unique identifier (UUID) scheme found')
            self.setEvaluationCriteriumScore('FsF-F1-01D-2',1, 'pass')
            self.result.test_status = 'pass'
            self.output.guid_scheme = 'uuid'
            self.output.guid = self.fuji.id
            self.maturity = 1
            self.score.earned = 1
        elif self.verify_hash(self.fuji.id):
            self.logger.log(self.fuji.LOG_SUCCESS,'FsF-F1-01D : Unique identifier (SHA,MD5) scheme found')
            self.setEvaluationCriteriumScore('FsF-F1-01D-2',1, 'pass')
            self.result.test_status = 'pass'
            self.output.guid_scheme = 'hash'
            self.output.guid = self.fuji.id
            self.maturity = 1
            self.score.earned = 1
        else:
            self.result.test_status = 'fail'
            self.score.earned = 0
            self.logger.warning('FsF-F1-01D : Failed to check the identifier scheme!.')
        self.result.score = self.score
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output
        self.result.maturity = self.maturity_levels.get(self.maturity)

    def verify_uuid(self,id):
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
