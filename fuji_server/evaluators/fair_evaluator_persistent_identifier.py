import idutils

from fuji_server import Persistence, PersistenceOutput
from fuji_server.evaluators.fair_evaluator import FAIREvaluator

from fuji_server.helper.metadata_mapper import Mapper

class FAIREvaluatorPersistentIdentifier(FAIREvaluator):

    def setPID(self, uid):
        self.pid = uid

    def evaluate(self):
        self.result = Persistence(id=self.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.logger.info('FsF-F1-02D : PID schemes-based assessment supported by the assessment service - {}'.format(
            Mapper.VALID_PIDS.value))
        if self.pid in Mapper.VALID_PIDS.value:
            self.pid_scheme = found_id
            # short_pid = id.normalize_pid(self.id, scheme=pid_scheme)
            self.pid_url = idutils.to_url(self.id, scheme=self.pid_scheme)
            self.logger.info('FsF-F1-02D : Persistence identifier scheme - {}'.format(self.pid_scheme))
        else:
            pid_score.earned = 0
            self.logger.warning('FsF-F1-02D : Not a persistent identifier scheme - {}'.format(found_id))
