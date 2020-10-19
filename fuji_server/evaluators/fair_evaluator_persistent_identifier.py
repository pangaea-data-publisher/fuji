import idutils
from fuji_server import Persistence, PersistenceOutput
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from urllib.parse import urlparse

class FAIREvaluatorPersistentIdentifier(FAIREvaluator):

    def evaluate(self):
        self.result = Persistence(id=self.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.logger.info('FsF-F1-02D : PID schemes-based assessment supported by the assessment service - {}'.format(
            Mapper.VALID_PIDS.value))
        if self.fuji.pid_scheme is not None:
            # short_pid = id.normalize_pid(self.id, scheme=pid_scheme)
            self.fuji.pid_url = idutils.to_url(self.id, scheme=self.fuji.pid_scheme)
            self.logger.info('FsF-F1-02D : Persistence identifier scheme - {}'.format(self.fuji.pid_scheme))
        else:
            self.score.earned = 0
            self.logger.warning('FsF-F1-02D : Not a persistent identifier scheme - {}'.format(self.fuji.id_scheme))

        # ======= RETRIEVE METADATA FROM LANDING PAGE =======
        requestHelper: RequestHelper = RequestHelper(self.fuji.pid_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.html)  # request
        neg_source, result = requestHelper.content_negotiate('FsF-F1-02D')
        #TODO: what if other protocols are used e.g. FTP etc..
        r = requestHelper.getHTTPResponse()
        if r:
            if r.status_code == 200:
                self.fuji.landing_url = r.url
                up = urlparse(self.fuji.landing_url)
                self.fuji.landing_origin = '{uri.scheme}://{uri.netloc}'.format(uri=up)
                self.fuji.landing_html = r.text
                if self.fuji.pid_scheme:
                    self.score.earned = self.total_score  # idenfier should be based on a persistence scheme and resolvable
                    self.output.pid = self.fuji.id
                    self.output.pid_scheme = self.fuji.pid_scheme
                    self.result.test_status = 'pass'
                self.output.resolved_url = self.fuji.landing_url  # url is active, although the identifier is not based on a pid scheme
                self.output.resolvable_status = True
                self.logger.info('FsF-F1-02D : Object identifier active (status code = 200)')
                self.fuji.isMetadataAccessible = True
            else:
                if r.status_code in [401, 402, 403]:
                    self.fuji.isMetadataAccessible = False
                #if r.status_code == 401:
                    #response = requests.get(self.pid_url, auth=HTTPBasicAuth('user', 'pass'))
                self.logger.warning("Resource inaccessible, identifier returned http status code: {code}".format(code=r.status_code))
        self.fuji.retrieve_metadata(result)
        self.result.score = self.score
        self.result.output = self.output
