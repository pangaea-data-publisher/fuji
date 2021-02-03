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

import logging

import idutils
from lxml import etree
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes

class RepositoryHelper:

    DATACITE_REPOSITORIES = Preprocessor.getRE3repositories()
    ns = {"r3d": "http://www.re3data.org/schema/2-2"}
    RE3DATA_APITYPES =['OAI-PMH','SOAP','SPARQL','SWORD','OpenDAP']

    def __init__(self, client, pidscheme):
        self.client_id = client
        self.pid_scheme = pidscheme
        self.re3metadata_raw = None
        self.repository_name = None
        self.repository_url = None
        self.repo_apis = {}
        self.repo_standards = []
        self.logger = Preprocessor.logger #logging.getLogger(__name__)
        print(__name__)
    def lookup_re3data(self):
        if self.client_id and self.pid_scheme:
            re3doi = RepositoryHelper.DATACITE_REPOSITORIES.get(self.client_id)  # {client_id,re3doi}
            short_re3doi = idutils.normalize_pid(re3doi, scheme='doi') #https://doi.org/10.17616/R3XS37
            # pid -> clientId -> repo doi-> re3id, and query repository metadata from re3api
            if re3doi:
                self.logger.info('Found match re3data (DOI-based) record')
                query_url = Preprocessor.RE3DATA_API + '?query=' + short_re3doi  # https://re3data.org/api/beta/repositories?query=
                q = RequestHelper(url=query_url)
                q.setAcceptType(AcceptTypes.xml)
                re_source, xml = q.content_negotiate(metric_id='RE3DATA')
                root = etree.fromstring(xml)
                #<link href="https://www.re3data.org/api/beta/repository/r3d100010134" rel="self" />
                re3link = root.xpath('//link')[0].attrib['href']
                if re3link is not None:
                    self.logger.info('Found match re3data metadata record')
                    # query reposiroty metadata
                    q2 = RequestHelper(url=re3link)
                    q2.setAcceptType(AcceptTypes.xml)
                    re3_source, re3_response = q2.content_negotiate(metric_id='RE3DATA')
                    self.re3metadata_raw = re3_response
                    self.parseRepositoryMetadata()
            else:
                self.logger.warning('No DOI of client id is available from datacite api')

    def parseRepositoryMetadata(self):
        #http://schema.re3data.org/3-0/re3data-example-V3-0.xml
        root = etree.fromstring(self.re3metadata_raw)
        # ns = {k: v for k, v in root.nsmap.items() if k}
        name = root.xpath('//r3d:repositoryName', namespaces=RepositoryHelper.ns)
        url = root.xpath('//r3d:repositoryURL', namespaces=RepositoryHelper.ns)
        if name:
            self.repository_name = name[0].text
        if url:
            self.repository_url = url[0].text
        apis = root.xpath('//r3d:api', namespaces=RepositoryHelper.ns)
        for a in apis:
            apiType = a.attrib['apiType']
            if apiType in RepositoryHelper.RE3DATA_APITYPES:
                self.repo_apis[a.attrib['apiType']] = a.text
        standards = root.xpath('//r3d:metadataStandard/r3d:metadataStandardName', namespaces=RepositoryHelper.ns)
        #we only use the name as the url specified in re3data is dcc-based, e.g., http://www.dcc.ac.uk/resources/metadata-standards/dif-directory-interchange-format
        self.repo_standards = [s.text for s in standards]

    def getRe3MetadataStandards(self):
        return self.repo_standards

    def getRe3MetadataAPIs(self):
        return self.repo_apis

    def getRepoNameURL(self):
        return self.repository_name, self.repository_url

