import idutils
from bs4 import BeautifulSoup

from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


class RepositoryHelper:

    DATACITE_REPOSITORIES = Preprocessor.getRE3repositories()

    def __init__(self, client, pidscheme):
        self.client_id = client
        self.pid_scheme = pidscheme
        self.re3metadata = None

    def lookup_re3data(self):
        if self.client_id:
            re3doi = RepositoryHelper.DATACITE_REPOSITORIES.get(self.client_id)  # {client_id,re3doi}
            short_re3doi = idutils.normalize_pid(re3doi, scheme=self.pid_scheme)
            # from short pid get clientId, use clientId to get local re3id, and query reposiroty metadata from re3api
            re3link = None
            if re3doi:
                query_url = Preprocessor.RE3DATA_API + '?query=' + short_re3doi  # https://re3data.org/api/beta/repositories?query=
                q = RequestHelper(url=query_url)
                q.setAcceptType(AcceptTypes.xml)
                resp = q.content_negotiate('RE3DATA')  # takes first record
                soup = BeautifulSoup(resp, "lxml")
                link_tag = soup.find_all('link')[0]
                re3link = link_tag.get("href")
                if re3link:
                    # query reposiroty metadata
                    q2 = RequestHelper(url=re3link)
                    q2.setAcceptType(AcceptTypes.xml)
                    self.re3metadata = q2.content_negotiate('RE3DATA')

    def getRe3Metadata(self):
        return self.re3metadata

            # policies
            # < r3d: metadataStandard >
            # < r3d: metadataStandardName
            # metadataStandardScheme = "DCC" > DDI - DataDocumentation itiative < / r3d: metadataStandardName >
            # < r3d: metadataStandardURL >
            # http: // www.dcc.ac.uk / resources / metadata - standards / ddi - data - documentation - initiative
            # < / r3d: metadataStandardURL >
            # < / r3d: metadataStandard >
            # <r3d: api apiType = "OAI-PMH" > http: // ws.pangaea.de / oai / < / r3d: api >
            # http://digitalcollections.uark.edu/oai/oai.php?verb=GetRecord&identifier=oai:digitalcollections.uark.edu:OzarkFolkSong/3092&metadataPrefix=oai_qdc
            # http://ws.pangaea.de/oai/provider?verb=ListMetadataFormats
            # http://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:pangaea.de:doi:10.1594/PANGAEA.66871
            # http://arXiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:cs/0112017&metadataPrefix=oai_dc
            # Sample OAI Identifier	oai:pangaea.de:doi:10.1594/PANGAEA.999999
            # Request: An identifier, in combination with a metadataPrefix, is used in the GetRecord request as a means of requesting a record in a specific metadata format from an item.
            # return None

