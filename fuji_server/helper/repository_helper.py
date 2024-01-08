# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import idutils
from lxml import etree
from tldextract import extract

from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.request_helper import AcceptTypes, RequestHelper


class RepositoryHelper:
    DATACITE_REPOSITORIES = Preprocessor.getRE3repositories()
    ns = {"r3d": "http://www.re3data.org/schema/2-2"}
    RE3DATA_APITYPES = ["OAI-PMH", "SOAP", "SPARQL", "SWORD", "OpenDAP"]

    def __init__(self, client_id, logger, landingpage):
        self.client_id = client_id
        self.logger = logger
        self.landing_page_url = landingpage
        # self.pid_scheme = pidscheme
        self.re3metadata_raw = None
        self.repository_name = None
        self.repository_url = None
        self.repo_apis = {}
        self.repo_standards = []
        # self.logger = logging.getLogger(logger)
        # print(__name__)

    def lookup_re3data(self):
        if self.client_id:  # and self.pid_scheme:
            re3doi = RepositoryHelper.DATACITE_REPOSITORIES.get(self.client_id)  # {client_id,re3doi}
            if re3doi:
                if idutils.is_doi(re3doi):
                    short_re3doi = idutils.normalize_pid(re3doi, scheme="doi")  # https://doi.org/10.17616/R3XS37
                else:
                    re3doi = None

            # pid -> clientId -> repo doi-> re3id, and query repository metadata from re3api
            if re3doi:
                self.logger.info("FsF-R1.3-01M : Found match re3data (DOI-based) record")
                query_url = (
                    Preprocessor.RE3DATA_API + "?query=" + short_re3doi
                )  # https://re3data.org/api/beta/repositories?query=
                q = RequestHelper(url=query_url)
                q.setAcceptType(AcceptTypes.xml)
                re_source, xml = q.content_negotiate(metric_id="RE3DATA")
                try:
                    if isinstance(xml, bytes):
                        xml = xml.decode().encode()
                    root = etree.fromstring(xml)

                    # <link href="https://www.re3data.org/api/beta/repository/r3d100010134" rel="self" />
                    re3link = root.xpath("//link")[0].attrib["href"]
                    if re3link is not None:
                        self.logger.info("FsF-R1.3-01M : Found match re3data metadata record -: " + str(re3link))
                        # query reposiroty metadata
                        q2 = RequestHelper(url=re3link)
                        q2.setAcceptType(AcceptTypes.xml)
                        re3_source, re3_response = q2.content_negotiate(metric_id="RE3DATA")
                        self.re3metadata_raw = re3_response
                        self.parseRe3data()
                except Exception as e:
                    self.logger.warning("FsF-R1.3-01M : Malformed re3data (DOI-based) record received: " + str(e))
            else:
                self.logger.warning("FsF-R1.3-01M : No DOI of client id is available from datacite api")

    def parseRe3data(self):
        # http://schema.re3data.org/3-0/re3data-example-V3-0.xml
        root = etree.fromstring(self.re3metadata_raw)
        # ns = {k: v for k, v in root.nsmap.items() if k}
        name = root.xpath("//r3d:repositoryName", namespaces=RepositoryHelper.ns)
        url = root.xpath("//r3d:repositoryURL", namespaces=RepositoryHelper.ns)
        if name:
            self.repository_name = name[0].text
        if url:
            self.repository_url = url[0].text
        repo_domain_verified = False
        repo_url_parts = extract(self.repository_url)
        landing_url_parts = extract(self.landing_page_url)
        repo_domain = repo_url_parts.domain + "." + repo_url_parts.suffix
        landing_domain = landing_url_parts.domain + "." + landing_url_parts.suffix
        if landing_domain == repo_domain:
            repo_domain_verified = True
            self.logger.info(
                "FsF-R1.3-01M : Domain name listed in re3data metadata record matches landing page domain-: "
                + str(repo_domain)
            )
        else:
            self.logger.warning(
                "FsF-R1.3-01M : Domain name listed in re3data metadata record does not match landing page domain, therefore ignoring re3data records -: "
                + str(repo_domain)
                + " - "
                + str(landing_domain)
            )
        if repo_domain_verified:
            apis = root.xpath("//r3d:api", namespaces=RepositoryHelper.ns)
            for a in apis:
                apiType = a.attrib["apiType"]
                if apiType in RepositoryHelper.RE3DATA_APITYPES:
                    self.repo_apis[a.attrib["apiType"]] = a.text
            # standards = root.xpath('//r3d:metadataStandard/r3d:metadataStandardName', namespaces=RepositoryHelper.ns)
            standards = root.xpath("//r3d:metadataStandard/r3d:metadataStandardURL", namespaces=RepositoryHelper.ns)
            self.repo_standards = [s.text for s in standards]
            # print('#### ', self.repo_standards)

    def getRe3MetadataStandards(self):
        return self.repo_standards

    def getRe3MetadataAPIs(self):
        return self.repo_apis

    def getRepoNameURL(self):
        return self.repository_name, self.repository_url
