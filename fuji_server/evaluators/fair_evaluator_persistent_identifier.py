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
from fuji_server import Persistence, PersistenceOutput
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from urllib.parse import urlparse

class FAIREvaluatorPersistentIdentifier(FAIREvaluator):

    def evaluate(self):
        self.result = Persistence(id=self.fuji.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.logger.info('FsF-F1-02D : PID schemes-based assessment supported by the assessment service - {}'.format(
            Mapper.VALID_PIDS.value))
        if self.fuji.pid_scheme is not None:
            # short_pid = id.normalize_pid(self.id, scheme=pid_scheme)
            self.fuji.pid_url = idutils.to_url(self.fuji.id, scheme=self.fuji.pid_scheme)
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
            if r.status == 200:
                self.fuji.landing_url = r.url
                up = urlparse(self.fuji.landing_url)
                self.fuji.landing_origin = '{uri.scheme}://{uri.netloc}'.format(uri=up)
                self.fuji.landing_html = requestHelper.getResponseContent()
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
