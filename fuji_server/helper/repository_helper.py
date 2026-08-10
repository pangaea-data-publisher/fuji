# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT
# import traceback

from idutils import is_doi, normalize_pid
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
        self.repourls = []  # from merged metadata
        self.repo_apis = {}
        self.repo_standards = []
        # self.logger = logging.getLogger(logger)
        # print(__name__)

    async def lookup_re3data(self):
        if self.client_id:  # and self.pid_scheme:
            re3doi = RepositoryHelper.DATACITE_REPOSITORIES.get(self.client_id)  # {client_id,re3doi}
            if re3doi:
                if is_doi(re3doi):
                    short_re3doi = normalize_pid(re3doi, scheme="doi")  # https://doi.org/10.17616/R3XS37
                else:
                    re3doi = None

            # pid -> clientId -> repo doi-> re3id, and query repository metadata from re3api
            if re3doi:
                self.logger.info("FsF-R1.3-01M : Found match re3data (DOI-based) record")
                query_url = (
                    Preprocessor.RE3DATA_API + "?query=" + short_re3doi
                )  # https://re3data.org/api/beta/repositories?query=
                q = RequestHelper(url=query_url, logInst=self.logger)
                q.setAcceptType(AcceptTypes.xml)
                _re_source, xml = await q.content_negotiate(metric_id="FsF-R1.3-01M")
                try:
                    if isinstance(xml, bytes):
                        xml = xml.decode().encode()
                    if isinstance(xml, str):
                        root = etree.fromstring(xml)
                        # <link href="https://www.re3data.org/api/beta/repository/r3d100010134" rel="self" />
                        re3link = root.xpath("//link")[0].attrib["href"]
                        if re3link is not None:
                            self.logger.info("FsF-R1.3-01M : Found match re3data metadata record -: " + str(re3link))
                            # query reposiroty metadata
                            q2 = RequestHelper(url=re3link, logInst=self.logger)
                            q2.setAcceptType(AcceptTypes.xml)
                            _re3_source, re3_response = await q2.content_negotiate(metric_id="FsF-R1.3-01M")
                            self.re3metadata_raw = re3_response
                            self.parseRe3data()
                except Exception as e:
                    # traceback.print_exc()
                    self.logger.warning(
                        "FsF-R1.3-01M : Malformed or none re3data (DOI-based) record received: E: " + str(e)
                    )
            else:
                self.logger.warning("FsF-R1.3-01M : No DOI of client id is available from datacite api")

    def parseRe3data(self):
        if self.re3metadata_raw:
            root = etree.fromstring(self.re3metadata_raw)
            # print(self.re3metadata_raw)
            # ns = {k: v for k, v in root.nsmap.items() if k}
            name = root.xpath("//r3d:repositoryName", namespaces=RepositoryHelper.ns)
            url = root.xpath("//r3d:repositoryURL", namespaces=RepositoryHelper.ns)
            re3id = root.xpath("//r3d:re3data.orgIdentifier", namespaces=RepositoryHelper.ns)
            apis = root.xpath("//r3d:api", namespaces=RepositoryHelper.ns)
            api_domains = []
            for a in apis:
                api_url_parts = extract(a.text)
                api_domain = api_url_parts.domain + "." + api_url_parts.suffix
                if api_domain not in api_domains:
                    api_domains.append(api_domain)
            if re3id:
                re3id = re3id[0].text
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
            elif landing_domain in api_domains:
                repo_domain_verified = True
                self.logger.info(
                    "FsF-R1.3-01M : Domain name listed in re3data metadata record matches one of the given API domains -: "
                    + str(api_domains)
                )
            else:
                self.logger.info(
                    "FsF-R1.3-01M : Domain name listed in re3data metadata record does not match landing page domain or one of the given API domains, requires additional check -: "
                    + str(repo_domain)
                    + " - "
                    + str(landing_domain)
                )

            # now verify against repo urls claimed in publisher property of merged metadata
            # print('REPOURLS: ',self.repourls)
            if not repo_domain_verified:
                for repourl in self.repourls:
                    ext = extract(repourl)
                    repo_domain = ".".join(p for p in (ext.domain, ext.suffix) if p)
                    if landing_domain == repo_domain or re3id in str(repourl):
                        self.logger.info(
                            "FsF-R1.3-01M : A re3dataid was claimed by the publisher, therefore re3data metadata will be considered -: "
                            + str(repo_domain)
                        )
                        repo_domain_verified = True
                        break

            if repo_domain_verified:
                # apis = root.xpath("//r3d:api", namespaces=RepositoryHelper.ns)
                for a in apis:
                    apiType = a.attrib["apiType"]
                    if apiType in RepositoryHelper.RE3DATA_APITYPES:
                        self.repo_apis[a.attrib["apiType"]] = a.text
                standards = root.xpath("//r3d:metadataStandard/r3d:metadataStandardURL", namespaces=RepositoryHelper.ns)
                self.repo_standards = [s.text for s in standards]
                # print('#### ', self.repo_standards)
            else:
                self.logger.warning(
                    "FsF-R1.3-01M : Domain names listed in re3data metadata record does not match landing page or re3dataid, therefore re3data metadata will be ignored -: "
                    + str(repo_domain)
                )
        else:
            self.logger.warning(
                "FsF-R1.3-01M : No metadata  received for re3data fore client -: " + str(self.client_id)
            )

    def getRe3MetadataStandards(self):
        return self.repo_standards

    def getRe3MetadataAPIs(self):
        return self.repo_apis

    def getRepoNameURL(self):
        return self.repository_name, self.repository_url
