import idutils

from fuji_server.models.uniqueness_output import UniquenessOutput
from fuji_server.models.uniqueness import Uniqueness
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_mapper import Mapper


class FAIREvaluatorUniqueIdentifier(FAIREvaluator):

    def evaluate(self):
        # ======= CHECK IDENTIFIER UNIQUENESS =======
        self.result = Uniqueness(id=self.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = UniquenessOutput()
        schemes = [i[0] for i in idutils.PID_SCHEMES]
        self.logger.info('FsF-F1-01D : Using idutils schemes')
        found_ids = idutils.detect_identifier_schemes(self.fuji.id)  # some schemes like PMID are generic
        if len(found_ids) > 0:
            self.logger.info('FsF-F1-01D : Unique identifier schemes found {}'.format(found_ids))
            self.output.guid = self.fuji.id
            self.score.earned = self.total_score
            # identify main scheme
            if len(found_ids) == 1 and found_ids[0] == 'url':  # only url included
                self.fuji.pid_url = self.fuji.id
                self.fuji.id_scheme = found_ids[0]
            else:
                if 'url' in found_ids:  # ['doi', 'url']
                    found_ids.remove('url')
            found_id = found_ids[0]  # TODO: take the first element of list, e.g., [doi, handle]
            if found_id in Mapper.VALID_PIDS.value:
                self.fuji.pid_scheme = found_id
            self.logger.info('FsF-F1-01D : Finalized unique identifier scheme - {}'.format(found_id))
            self.output.guid_scheme = found_id
            self.result.test_status = 'pass'
            self.result.score = self.score
            self.result.output = self.output
        else:
            self.logger.warning('FsF-F1-01D : Failed to check the identifier scheme!.')
