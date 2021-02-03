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
import idutils

from fuji_server.models.uniqueness_output import UniquenessOutput
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_mapper import Mapper


class FAIREvaluatorUniqueIdentifier(FAIREvaluator):

    def evaluate(self):
        # ======= CHECK IDENTIFIER UNIQUENESS =======
        self.result = Uniqueness(id=self.fuji.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = UniquenessOutput()
        schemes = [i[0] for i in idutils.PID_SCHEMES]
        self.logger.info('FsF-F1-01D : Using idutils schemes')
        found_ids = idutils.detect_identifier_schemes(self.fuji.id)  # some schemes like PMID are generic
        if len(found_ids) > 0:
            self.logger.log(self.fuji.LOG_SUCCESS,'FsF-F1-01D : Unique identifier schemes found {}'.format(found_ids))
            self.setEvaluationCriteriumScore('FsF-F1-01D-1',1, 'pass')
            self.output.guid = self.fuji.id
            self.score.earned = self.total_score
            # identify main scheme
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
            if found_id in Mapper.VALID_PIDS.value:
                self.fuji.pid_scheme = found_id
            self.logger.info('FsF-F1-01D : Finalized unique identifier scheme - {}'.format(found_id))
            self.output.guid_scheme = found_id
            self.result.test_status = 'pass'
            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
        else:
            self.logger.warning('FsF-F1-01D : Failed to check the identifier scheme!.')
