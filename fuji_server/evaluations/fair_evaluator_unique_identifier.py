import logging

import idutils

from fuji_server.helper.log_message_filter import MessageFilter
from fuji_server.models.uniqueness_output import UniquenessOutput

from fuji_server.models.uniqueness import Uniqueness

from fuji_server.client.evaluations.fair_evaluator import FAIREvaluator


class FAIREvaluatorUniqueIdentifier(FAIREvaluator):

    def setID(self, uid):
        self.id = uid

    def evaluate(self):
        # ======= CHECK IDENTIFIER UNIQUENESS =======
        self.result = Uniqueness(id=self.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = UniquenessOutput()
        schemes = [i[0] for i in idutils.PID_SCHEMES]
        self.logger.info('FsF-F1-01D : Using idutils schemes')
        found_ids = idutils.detect_identifier_schemes(self.id)  # some schemes like PMID are generic
        if len(found_ids) > 0:
            self.logger.info('FsF-F1-01D : Unique identifier schemes found {}'.format(found_ids))
            self.output.guid = self.id
            self.score.earned = self.total_score
            # identify main scheme
            if len(found_ids) == 1 and found_ids[0] == 'url':  # only url included
                self.pid_url = self.id
            else:
                if 'url' in found_ids:  # ['doi', 'url']
                    found_ids.remove('url')

            found_id = found_ids[0]  # TODO: take the first element of list, e.g., [doi, handle]
            self.logger.info('FsF-F1-01D : Finalized unique identifier scheme - {}'.format(found_id))
            self.output.guid_scheme = found_id
            self.result.test_status = 'pass'
            self.result.score = self.score
            self.result.output = self.output
