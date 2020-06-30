# -*- coding: utf-8 -*-
import json
import logging
import mimetypes
import re
import urllib
import urllib.request as urllib
from typing import List, Any
from urllib.parse import urlparse

import requests
from SPARQLWrapper import SPARQLWrapper
from fuzzywuzzy import process, fuzz
import Levenshtein
import idutils
import lxml

from fuji_server.helper.log_message_filter import MessageFilter
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.metadata_collector_datacite import MetaDataCollectorDatacite
from fuji_server.helper.metadata_collector_dublincore import MetaDataCollectorDublinCore
from fuji_server.helper.metadata_collector_schemaorg import MetaDataCollectorSchemaOrg
from fuji_server.helper.metadata_collector_rdf import MetaDataCollectorRdf
from fuji_server.helper.metadata_provider_oai import OAIMetadataProvider
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.metadata_provider_sparql import SPARQLMetadataProvider
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.repository_helper import RepositoryHelper
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from fuji_server.models import *
from fuji_server.models import CoreMetadataOutput, CommunityEndorsedStandardOutputInner
from fuji_server.models.data_content_metadata import DataContentMetadata
from fuji_server.models.data_content_metadata_output import DataContentMetadataOutput
from fuji_server.models.data_content_metadata_output_inner import DataContentMetadataOutputInner
from fuji_server.models.data_provenance import DataProvenance
from fuji_server.models.data_provenance_output import DataProvenanceOutput


class FAIRCheck:
    METRICS = None
    SPDX_LICENSES = None
    SPDX_LICENSE_NAMES = None
    COMMUNITY_STANDARDS_NAMES = None
    COMMUNITY_STANDARDS = None
    SCIENCE_FILE_FORMATS = None
    LONG_TERM_FILE_FORMATS = None
    OPEN_FILE_FORMATS = None

    def __init__(self, uid, test_debug=False):
        self.id = uid
        self.oaipmh_endpoint = None
        self.pid_url = None  # full pid # e.g., "https://doi.org/10.1594/pangaea.906092 or url (non-pid)
        self.landing_url = None  # url of the landing page of self.pid_url
        self.landing_html = None
        self.landing_origin = None  # schema + authority of the landing page e.g. https://www.pangaea.de
        self.pid_scheme = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metadata_sources = []
        self.isDebug = test_debug
        self.isRestricted = False
        self.metadata_merged = {}
        self.content_identifier=[]
        self.community_standards = []
        self.community_standards_uri = {}
        self.namespace_uri=[]
        self.reference_elements = Mapper.REFERENCE_METADATA_LIST.value.copy()  # all metadata elements required for FUJI metrics
        self.related_resources = []
        self.test_data_content_text = None# a helper to check metadata against content
        self.sparql_endpoint = None
        self.rdf_collector = None
        if self.isDebug:
            self.msg_filter = MessageFilter()
            self.logger.addFilter(self.msg_filter)
            self.logger.setLevel(logging.INFO)  # set to debug in testing environment
        self.count = 0
        FAIRCheck.load_predata()
        self.extruct = None

    @classmethod
    def load_predata(cls):
        if not cls.METRICS:
            cls.METRICS = Preprocessor.get_custom_metrics(['metric_name', 'total_score'])
        if not cls.SPDX_LICENSES:
            # cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES, cls.SPDX_LICENSE_URLS = Preprocessor.get_licenses()
            cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES = Preprocessor.get_licenses()
        if not cls.COMMUNITY_STANDARDS:
            cls.COMMUNITY_STANDARDS = Preprocessor.get_metadata_standards()
            cls.COMMUNITY_STANDARDS_NAMES = list(cls.COMMUNITY_STANDARDS.keys())
        if not cls.SCIENCE_FILE_FORMATS:
            cls.SCIENCE_FILE_FORMATS = Preprocessor.get_science_file_formats()
        if not cls.LONG_TERM_FILE_FORMATS:
            cls.LONG_TERM_FILE_FORMATS = Preprocessor.get_long_term_file_formats()
        if not cls.OPEN_FILE_FORMATS:
            cls.OPEN_FILE_FORMATS = Preprocessor.get_open_file_formats()
        # if not cls.DATACITE_REPOSITORIES:
        # cls.DATACITE_REPOSITORIES = Preprocessor.getRE3repositories()

    @staticmethod
    def uri_validator(u):  # TODO integrate into request_helper.py
        try:
            r = urlparse(u)
            return all([r.scheme, r.netloc])
        except:
            return False

    def check_unique_persistent(self):
        uid_metric_identifier = 'FsF-F1-01D'  # FsF-F1-01D: Globally unique identifier
        pid_metric_identifier = 'FsF-F1-02D'  # FsF-F1-02D: Persistent identifier
        uid_metric_name = FAIRCheck.METRICS.get(uid_metric_identifier).get('metric_name')
        pid_metric_name = FAIRCheck.METRICS.get(pid_metric_identifier).get('metric_name')
        self.count += 1
        uid_result = Uniqueness(id=self.count, metric_identifier=uid_metric_identifier, metric_name=uid_metric_name)
        self.count += 1
        pid_result = Persistence(id=self.count, metric_identifier=pid_metric_identifier, metric_name=pid_metric_name)
        uid_sc = int(FAIRCheck.METRICS.get(uid_metric_identifier).get('total_score'))
        pid_sc = int(FAIRCheck.METRICS.get(pid_metric_identifier).get('total_score'))
        uid_score = FAIRResultCommonScore(total=uid_sc)
        pid_score = FAIRResultCommonScore(total=pid_sc)
        uid_output = UniquenessOutput()
        pid_output = PersistenceOutput()

        # ======= CHECK IDENTIFIER UNIQUENESS =======
        found_ids = idutils.detect_identifier_schemes(self.id)  # some schemes like PMID are generic
        if len(found_ids) > 0:
            self.logger.info('FsF-F1-01D : Unique identifier schemes found {}'.format(found_ids))
            uid_output.guid = self.id
            uid_score.earned = uid_sc
            # identify main scheme
            if len(found_ids) == 1 and found_ids[0] == 'url':  # only url included
                self.pid_url = self.id
            else:
                if 'url' in found_ids:  # ['doi', 'url']
                    found_ids.remove('url')

            found_id = found_ids[0]  # TODO: take the first element of list, e.g., [doi, handle]
            self.logger.info('FsF-F1-01D : Finalized unique identifier scheme - {}'.format(found_id))
            uid_output.guid_scheme = found_id
            uid_result.test_status = 'pass'
            uid_result.score = uid_score
            uid_result.output = uid_output

            # ======= CHECK IDENTIFIER PERSISTENCE =======
            if found_id in Mapper.VALID_PIDS.value:
                self.pid_scheme = found_id
                # short_pid = id.normalize_pid(self.id, scheme=pid_scheme)
                self.pid_url = idutils.to_url(self.id, scheme=self.pid_scheme)
                self.logger.info('FsF-F1-02D : Persistence identifier scheme - {}'.format(self.pid_scheme))
            else:
                pid_score.earned = 0
                self.logger.warning('FsF-F1-02D : Not a persistent identifier scheme - {}'.format(found_id))

            # ======= RETRIEVE METADATA FROM LANDING PAGE =======
            requestHelper: RequestHelper = RequestHelper(self.pid_url, self.logger)
            requestHelper.setAcceptType(AcceptTypes.html)  # request
            result = requestHelper.content_negotiate('FsF-F1-02D')
            r = requestHelper.getHTTPResponse()
            if r:
                if r.status_code == 200:
                    self.landing_url = r.url
                    up = urlparse(self.landing_url)
                    self.landing_origin = '{uri.scheme}://{uri.netloc}'.format(uri=up)
                    self.landing_html = r.text
                    if self.pid_scheme:
                        pid_score.earned = pid_sc  # idenfier should be based on a persistence scheme and resolvable
                        pid_output.pid = self.id
                        pid_output.pid_scheme = self.pid_scheme
                        pid_result.test_status = 'pass'
                    pid_output.resolved_url = self.landing_url  # url is active, although the identifier is not based on a pid scheme
                    pid_output.resolvable_status = True
            pid_result.score = pid_score
            pid_result.output = pid_output

            if self.isDebug:
                uid_result.test_debug = self.msg_filter.getMessage(uid_metric_identifier)
                pid_result.test_debug = self.msg_filter.getMessage(pid_metric_identifier)
        else:
            self.logger.warning('FsF-F1-01D : Failed to check the identifier scheme!.')

        self.retrieve_metadata(result)
        return uid_result.to_dict(), pid_result.to_dict()

    def retrieve_metadata(self, extruct_metadata):
        if isinstance(extruct_metadata, dict):
            embedded_exists = {k: v for k, v in extruct_metadata.items() if v}
            self.extruct = embedded_exists.copy()
            self.logger.info(
                'FsF-F2-01M : Formats of structured metadata embedded in HTML markup {}'.format(embedded_exists.keys()))
            if embedded_exists:  # retrieve metadata from landing page
                self.retrieve_metadata_embedded(embedded_exists)
        else:
            self.logger.warning('FsF-F2-01M : No structured metadata embedded in HTML')

        if self.reference_elements:  # this will be always true as we need datacite client id
            self.retrieve_metadata_external()

        # ========= clean merged metadata, delete all entries which are None or ''
        for mk, mv in list(self.metadata_merged.items()):
            if mv == '' or mv is None:
                del self.metadata_merged[mk]

        self.logger.info('FsF-F2-01M : Type of object described by the metadata - {}'.format(self.metadata_merged.get('object_type')))

        # detect api and standards
        self.retrieve_apis_standards()

    def retrieve_apis_standards(self):
        self.logger.info('FsF-R1.3-01M : Retrieving API and Standards from R3DATA')
        client_id = self.metadata_merged.get('datacite_client')
        self.logger.info('FsF-R1.3-01M : R3DATA/Datacite client id - {}'.format(client_id))
        if client_id and self.pid_scheme:
            repoHelper = RepositoryHelper(client_id, self.pid_scheme)
            repoHelper.lookup_re3data()
            self.oaipmh_endpoint = repoHelper.getRe3MetadataAPIs().get('OAI-PMH')
            self.sparql_endpoint = repoHelper.getRe3MetadataAPIs().get('SPARQL')
            self.community_standards = repoHelper.getRe3MetadataStandards()
            if self.community_standards:
                self.logger.info('{} : Metadata standards defined in R3DATA - {}'.format('FsF-R1.3-01M',self.community_standards))
            else: # fallback get standards defined in api, e.g., oai-pmh
                self.logger.info(
                    '{} : OAIPMH endpoint from R3DATA {}'.format('FsF-R1.3-01M', self.oaipmh_endpoint))
                if (self.uri_validator(self.oaipmh_endpoint)):
                    oai_provider = OAIMetadataProvider(endpoint=self.oaipmh_endpoint, logger=self.logger, metric_id='FsF-R1.3-01M')
                    self.community_standards_uri = oai_provider.getMetadataStandards()
                    self.namespace_uri.extend(oai_provider.getNamespaces())
                    self.logger.info('{} : Metadata standards defined in R3DATA - {}'.format('FsF-R1.3-01M', self.community_standards_uri))

    def retrieve_metadata_embedded(self, extruct_metadata):
        # ========= retrieve schema.org (embedded, or from via content-negotiation if pid provided) =========
        isPid = False
        if self.pid_scheme:
            isPid = True
        ext_meta = extruct_metadata.get('json-ld')
        schemaorg_collector = MetaDataCollectorSchemaOrg(loggerinst=self.logger, sourcemetadata=ext_meta,
                                                         mapping=Mapper.SCHEMAORG_MAPPING,
                                                         ispid=isPid, pidurl=self.pid_url)
        source_schemaorg, schemaorg_dict = schemaorg_collector.parse_metadata()
        if schemaorg_dict:
            self.namespace_uri.extend(schemaorg_collector.namespaces)
            not_null_sco = [k for k, v in schemaorg_dict.items() if v is not None]
            self.metadata_sources.append(source_schemaorg)
            if schemaorg_dict.get('related_resources'):
                self.related_resources.extend(schemaorg_dict.get('related_resources'))
            # add object type for future reference
            for i in not_null_sco:
                if i in self.reference_elements:
                    self.metadata_merged[i] = schemaorg_dict[i]
                    self.reference_elements.remove(i)
        else:
            self.logger.info('FsF-F2-01M : Schema.org metadata UNAVAILABLE')

        # ========= retrieve dublin core embedded in html page =========
        if self.reference_elements:
            dc_collector = MetaDataCollectorDublinCore(loggerinst=self.logger, sourcemetadata=self.landing_html,
                                                       mapping=Mapper.DC_MAPPING)
            source_dc, dc_dict = dc_collector.parse_metadata()
            if dc_dict:
                self.namespace_uri.extend(dc_collector.namespaces)
                not_null_dc = [k for k, v in dc_dict.items() if v is not None]
                self.metadata_sources.append(source_dc)
                if dc_dict.get('related_resources'):
                    self.related_resources.extend(dc_dict.get('related_resources'))
                for d in not_null_dc:
                    if d in self.reference_elements:
                        self.metadata_merged[d] = dc_dict[d]
                        self.reference_elements.remove(d)
            else:
                self.logger.info('FsF-F2-01M : DublinCore metadata UNAVAILABLE')

        # ========= retrieve typed links =========
        if self.metadata_merged.get('object_content_identifier') is None:
            links = self.get_html_typed_links(rel='item')
            if links:
                self.metadata_sources.append(MetaDataCollector.Sources.SIGN_POSTING.value)


    # Comment: not sure if we really need a separate class as proposed below. Instead we can use a dictionary
    # TODO (important) separate class to represent https://www.iana.org/assignments/link-relations/link-relations.xhtml
    # use IANA relations for extracting metadata and meaningful links
    def get_html_typed_links(self, rel="item"):
        # Use Typed Links in HTTP Link headers to help machines find the resources that make up a publication.
        # Use links to find domains specific metadata
        datalinks = []
        if isinstance(self.landing_html, str):
            dom = lxml.html.fromstring(self.landing_html.encode('utf8'))
            links=dom.xpath('/*/head/link[@rel="'+rel+'"]')
            for l in links:
                href=l.attrib.get('href')
                #handle relative paths
                if href.startswith('/'):
                    href=self.landing_origin+href
                datalinks.append({'url': href, 'type': l.attrib.get('type'), 'rel': l.attrib.get('rel'), 'profile': l.attrib.get('format')})
        return datalinks

    def retrieve_metadata_external(self):
        # ========= retrieve datacite json metadata based on pid =========
        if self.pid_scheme:
            dcite_collector = MetaDataCollectorDatacite(mapping=Mapper.DATACITE_JSON_MAPPING, loggerinst=self.logger,
                                                        pid_url=self.pid_url)
            source_dcitejsn, dcitejsn_dict = dcite_collector.parse_metadata()
            if dcitejsn_dict:
                not_null_dcite = [k for k, v in dcitejsn_dict.items() if v is not None]
                # self.logger.info('FsF-F2-01M : Found Datacite metadata {} '.format(not_null_dcite))
                self.metadata_sources.append(source_dcitejsn)
                if dcitejsn_dict.get('related_resources'):
                    self.related_resources.extend(dcitejsn_dict.get('related_resources'))
                for r in not_null_dcite:
                    if r in self.reference_elements:
                        self.metadata_merged[r] = dcitejsn_dict[r]
                        self.reference_elements.remove(r)
            else:
                self.logger.info('FsF-F2-01M : Datacite metadata UNAVAILABLE')
        else:
            self.logger.info('FsF-F2-01M : Not a PID, therefore Datacite metadata (json) not requested.')

        found_metadata_link = False
        typed_metadata_links = self.get_html_typed_links(rel='alternate')
        for metadata_link in typed_metadata_links:
            if metadata_link['type'] in ['application/rdf+xml','text/n3','text/ttl','application/ld+json']:
                self.logger.info('FsF-F2-01M : Found Typed Links in HTML Header linking to RDF Metadata ('+str(metadata_link['type']+')'))
                found_metadata_link=True
                source = MetaDataCollector.Sources.RDF_SIGN_POSTING.value
                self.rdf_collector = MetaDataCollectorRdf(loggerinst=self.logger, target_url=metadata_link['url'], source=source )
                break

        if not found_metadata_link:
            #TODO: find a condition to trigger the rdf request
            source = MetaDataCollector.Sources.LINKED_DATA.value
            self.rdf_collector = MetaDataCollectorRdf(loggerinst=self.logger, target_url=self.landing_url, source=source)

        if self.rdf_collector is not None:
            source_rdf, rdf_dict = self.rdf_collector.parse_metadata()
            self.namespace_uri.extend(self.rdf_collector.getNamespaces())
            if rdf_dict:
                not_null_rdf = [k for k, v in rdf_dict.items() if v is not None]
                # self.logger.info('FsF-F2-01M : Found Datacite metadata {} '.format(not_null_dcite))
                self.metadata_sources.append(source_rdf)
                for r in not_null_rdf:
                    if r in self.reference_elements:
                        self.metadata_merged[r] = rdf_dict[r]
                        self.reference_elements.remove(r)
            else:
                self.logger.info('FsF-F2-01M : Linked Data metadata UNAVAILABLE')

        if self.reference_elements:
            self.logger.debug('Reference metadata elements NOT FOUND - {}'.format(self.reference_elements))
            # TODO (Important) - search via b2find
        else:
            self.logger.debug('FsF-F2-01M : ALL reference metadata elements available')

    def check_minimal_metatadata(self):
        self.count += 1
        coremeta_identifier = 'FsF-F2-01M'
        meta_sc = int(FAIRCheck.METRICS.get(coremeta_identifier).get('total_score'))
        meta_score = FAIRResultCommonScore(total=meta_sc)
        coremeta_name = FAIRCheck.METRICS.get(coremeta_identifier).get('metric_name')
        meta_result = CoreMetadata(id=self.count, metric_identifier=coremeta_identifier, metric_name=coremeta_name)
        metadata_required = Mapper.REQUIRED_CORE_METADATA.value
        metadata_found = {k: v for k, v in self.metadata_merged.items() if k in metadata_required}
        self.logger.info('FsF-F2-01M : Required core metadata {}'.format(metadata_required))

        partial_elements = ['creator', 'title', 'object_identifier', 'publication_date']
        #TODO: check the number of metadata elements which metadata_found has in common with metadata_required
        #set(a) & set(b)
        if set(metadata_found) == set(metadata_required):
            metadata_status = 'all metadata'
            meta_score.earned = meta_sc
            test_status = 'pass'
        elif set(partial_elements).issubset(metadata_found):
            metadata_status = 'partial metadata'
            meta_score.earned = meta_sc - 1
            test_status = 'pass'
        else:
            metadata_status = 'no metadata' # status should follow enumeration in yaml
            meta_score.earned = 0
            test_status = 'fail'

        missing = list(set(metadata_required) - set(metadata_found))
        if missing:
            self.logger.warning('FsF-F2-01M : Missing core metadata %s' % (missing))

        meta_output: CoreMetadataOutput = CoreMetadataOutput(core_metadata_status=metadata_status,
                                                             core_metadata_source=self.metadata_sources)
        meta_output.core_metadata_found = metadata_found
        meta_result.test_status = test_status
        meta_result.score = meta_score
        meta_result.output = meta_output
        if self.isDebug:
            meta_result.test_debug = self.msg_filter.getMessage(coremeta_identifier)
        return meta_result.to_dict()

    def check_content_identifier_included(self):
        self.count += 1
        did_included_identifier = 'FsF-F3-01M'  # FsF-F3-01M: Inclusion of data identifier in metadata
        included_name = FAIRCheck.METRICS.get(did_included_identifier).get('metric_name')
        did_result = IdentifierIncluded(id=self.count, metric_identifier=did_included_identifier, metric_name=included_name)
        did_sc = int(FAIRCheck.METRICS.get(did_included_identifier).get('total_score'))
        did_score = FAIRResultCommonScore(total=did_sc)
        did_output = IdentifierIncludedOutput()

        id_object = None
        id_object = self.metadata_merged.get('object_identifier')
        did_output.object_identifier_included = id_object
        contents = self.metadata_merged.get('object_content_identifier')
        self.logger.info('FsF-F3-01M : Data object identifier specified {}'.format(id_object))

        score = 0
        if FAIRCheck.uri_validator(
                id_object):  # TODO: check if specified identifier same is provided identifier (handle pid and non-pid cases)
            # check resolving status
            try:
                request = requests.get(id_object)
                if request.status_code == 200:
                    #TODO: handle binary content
                    if self.test_data_content_text == None:
                        self.test_data_content_text = request.text
                    self.logger.info('FsF-F3-01M : Data object identifier active (status code = 200)')
                    score += 1
                else:
                    if request.status_code in [401,402,403]:
                        self.isRestricted = True
                    self.logger.warning("Identifier returned response code: {code}".format(code=request.status_code))
            except:
                self.logger.warning('FsF-F3-01M : Object identifier does not exist or could not be accessed {}'.format(id_object))
        else:
            self.logger.warning('FsF-F3-01M : Invalid Identifier - {}'.format(id_object))

        content_list = []
        if contents:
            if isinstance(contents, dict):
                contents = [contents]
            contents = [c for c in contents if c]
            for content_link in contents:
                if content_link.get('url'):
                    self.logger.info('FsF-F3-01M : Data object (content) identifier included {}'.format(content_link.get('url')))
                    did_output_content = IdentifierIncludedOutputInner()
                    did_output_content.content_identifier_included = content_link
                    try:
                        # only check the status, do not download the content
                        response=urllib.urlopen(content_link.get('url'))
                        content_link['header_content_type'] = response.getheader('Content-Type')
                        content_link['header_content_type'] = str(content_link['header_content_type']).split(';')[0]
                        content_link['header_content_length'] = response.getheader('Content-Length')

                        if content_link['header_content_type'] != content_link.get('type'):
                            self.logger.warning('FsF-F3-01M : Content type given in metadata ('+str(content_link.get('type'))+') differs from content type given in Header response ('+str(content_link['header_content_type'])+')')
                            self.logger.info('FsF-F3-01M : Replacing metadata content type with content type from Header response: '+str(content_link['header_content_type']))
                            content_link['type'] = content_link['header_content_type']
                        #will pass even if the url cannot be accessed which is OK
                        #did_result.test_status = "pass"
                        #did_score.earned=1
                    except urllib.HTTPError as e:
                        self.logger.warning(
                            'FsF-F3-01M : Content identifier {0}, HTTPError code {1} '.format(content_link.get('url'), e.code))
                    except urllib.URLError as e:
                        self.logger.exception(e.reason)
                    except:
                        self.logger.warning('FsF-F3-01M : Could not access the resource')
                    else:  # will be executed if there is no exception
                        self.content_identifier.append(content_link)
                        did_output_content.content_identifier_active = True
                        content_list.append(did_output_content)
                else:
                    self.logger.warning('FsF-F3-01M : Data (content) url is empty - {}'.format(content_link))

        else:
            self.logger.warning('FsF-F3-01M : Data (content) identifier is missing.')

        if content_list:
            score += 1
        did_score.earned = score
        if score > 0: # 1 or 2 assumed to be 'pass'
            did_result.test_status = "pass"

        did_output.content = content_list
        did_result.output = did_output
        did_result.score = did_score

        if self.isDebug:
            did_result.test_debug = self.msg_filter.getMessage(did_included_identifier)
        return did_result.to_dict()

    def check_data_access_level(self):
        #Focus on machine readable rights -> URIs only
        #1) http://vocabularies.coar-repositories.org/documentation/access_rights/ check for http://purl.org/coar/access_right
        #2) Eprints AccessRights Vocabulary: check for http://purl.org/eprint/accessRights/
        #3) EU publications access rights check for http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC
        #4) CreativeCommons check for https://creativecommons.org/licenses/
        #5) Openaire Guidelines <dc:rights>info:eu-repo/semantics/openAccess</dc:rights>
        self.count += 1
        access_identifier = 'FsF-A1-01M'
        access_name = FAIRCheck.METRICS.get(access_identifier).get('metric_name')
        access_sc = int(FAIRCheck.METRICS.get(access_identifier).get('total_score'))
        access_score = FAIRResultCommonScore(total=access_sc)
        access_result = DataAccessLevel(self.count, metric_identifier=access_identifier, metric_name=access_name)
        access_output = DataAccessOutput()
        #rights_regex = r'((\/licenses|purl.org\/coar\/access_right|purl\.org\/eprint\/accessRights|europa\.eu\/resource\/authority\/access-right)\/{1}(\S*))'
        rights_regex = r'((creativecommons\.org|purl\.org|\/coar\access_right|purl\.org\/eprint\/accessRights|europa\.eu|\/resource\/authority\/access-right)\/{1}(\S*)|info\:eu-repo\/semantics\/\w+)'

        access_level = None
        access_details = {}
        score = 0
        test_status = "fail"
        exclude = []
        access_rights = self.metadata_merged.get('access_level')
        if access_rights is not None:
            self.logger.info('FsF-A1-01M : Found access rights information in dedicated metadata element')
            if isinstance(access_rights, str):
                access_rights = [access_rights]
            for access_right in access_rights:
                self.logger.info('FsF-A1-01M : Access information specified - {}'.format(access_right))
                if not self.isLicense(access_right, access_identifier):  # exclude license-based text from access_rights
                    rights_match = re.search(rights_regex, access_right, re.IGNORECASE)
                    if rights_match is not None:
                        for right_code, right_status in Mapper.ACCESS_RIGHT_CODES.value.items():
                            if re.search(right_code, rights_match[1], re.IGNORECASE):
                                access_level = right_status
                                access_details['access_condition'] = rights_match[1] #overwrite existing condition
                                self.logger.info('FsF-A1-01M : Access level recognized as ' + str(right_status))
                                break
                        break
                else:
                    self.logger.warning('FsF-A1-01M : Access condition looks like license, therefore the following is ignored - {}'.format(access_right))
                    exclude.append(access_right)
            if not access_details and access_rights:
                access_rights = set(access_rights) - set(exclude)
                if access_rights :
                    access_details['access_condition'] = ', '.join(access_rights)
        else:
            self.logger.warning('FsF-A1-01M : No access information is available in metadata')
            score = 0

        if access_level is None:
            # fall back - use binary access
            access_free = self.metadata_merged.get('access_free')
            if access_free is not None:
                self.logger.info('FsF-A1-01M : Used \'schema.org/isAccessibleForFree\' to determine the access level (either public or restricted)')
                if access_free: # schema.org: isAccessibleForFree || free
                    access_level = "public"
                else:
                    access_level = "restricted"
                access_details['accessible_free'] = access_free
            #TODO assume access_level = restricted if access_rights provided?

        #if embargoed, publication date must be specified (for now score is not deducted, just outputs warning message)
        if access_level == 'embargoed':
            available_date = self.metadata_merged.get('publication_date')
            if available_date:
                self.logger.info('FsF-A1-01M : Embargoed access, available date - {}'.format(available_date))
                access_details['available_date'] = available_date
            else:
                self.logger.warning('FsF-A1-01M : Embargoed access, available date NOT found')

        if access_level or access_details:
            score = 1
            test_status = "pass"
        #if access_details:
            #score += 1
        #if score > 1:
            #test_status = "pass"

        access_score.earned = score
        access_result.score = access_score
        access_result.test_status = test_status
        if access_level: #must be one of ['public', 'embargoed', 'restricted', 'closed_metadataonly']
            access_output.access_level = access_level
        else:
            self.logger.warning('FsF-A1-01M : Unable to determine the access level')
        access_output.access_details = access_details
        access_result.output = access_output
        if self.isDebug:
            access_result.test_debug = self.msg_filter.getMessage(access_identifier)
        return access_result.to_dict()

    def isLicense (self, value, metric_id):
        islicense = False
        isurl = idutils.is_url(value)
        spdx_html = None
        spdx_osi = None
        if isurl:
            spdx_html, spdx_osi = self.lookup_license_by_url(value, metric_id)
        else:
            spdx_html, spdx_osi = self.lookup_license_by_name(value, metric_id)
        if spdx_html or spdx_osi:
            islicense = True
        return islicense

    # def check_data_access_level_old(self):
    #     #Focus on machine readable rights -> URIs only
    #     #1) http://vocabularies.coar-repositories.org/documentation/access_rights/ check for http://purl.org/coar/access_right
    #     #2) Eprints AccessRights Vocabulary: check for http://purl.org/eprint/accessRights/
    #     #3) EU publications access rights check for http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC
    #     #4) CreativeCommons check for https://creativecommons.org/licenses/
    #     #5) <dc:rights>info:eu-repo/semantics/openAccess</dc:rights>
    #     self.count += 1
    #     access_identifier = 'FsF-A1-01M'
    #     access_name = FAIRCheck.METRICS.get(access_identifier).get('metric_name')
    #     access_sc = int(FAIRCheck.METRICS.get(access_identifier).get('total_score'))
    #     access_score = FAIRResultCommonScore(total=access_sc)
    #     access_result = DataAccessLevel(self.count, metric_identifier=access_identifier, metric_name=access_name)
    #     access_output = DataAccessOutput()
    #     rights_regex = r'((creativecommons\.org\/licenses|purl.org\/coar\/access_right|purl\.org\/eprint\/accessRights|europa\.eu\/resource\/authority\/access-right)\/{1}(\S*))'
    #     access_rights = self.metadata_merged.get('access_level')
    #
    #     if access_rights is not None:
    #         self.logger.info('FsF-A1-01M : Found access rights information in dedicated metadata element')
    #     if isinstance(access_rights, str):
    #         access_rights = [access_rights]
    #     if isinstance(access_rights, bool):
    #         if access_rights:
    #             access_output.access_level = "public"
    #         else:
    #             access_output.access_level = "restricted"
    #         access_output.access_details = {'access_right': {'https://schema.org/isAccessibleForFree': access_rights}}
    #         access_score.earned = 1
    #         access_result.test_status = "pass"
    #     else:
    #         access_licenses = self.metadata_merged.get('license')
    #         if access_licenses is not None:
    #             if isinstance(access_licenses, str):
    #                 access_licenses=[access_licenses]
    #             if access_rights is not None:
    #                 access_licenses.extend(access_rights)
    #             for access_right in access_licenses:
    #                 rights_match = re.search(rights_regex, access_right)
    #                 if rights_match is not None:
    #                     access_result.test_status = "pass"
    #                     for right_code, right_status in Mapper.ACCESS_RIGHT_CODES.value.items():
    #                         if re.search(right_code,rights_match[1]):
    #                             access_output.access_level = right_status
    #                             access_score.earned = 1
    #                             self.logger.info('FsF-A1-01M : Rights information recognized as: '+str(right_status))
    #                             break
    #                     self.logger.info('FsF-A1-01M : Found access rights information in metadata')
    #                     access_output.access_details={'access_right': rights_match[1]}
    #                     break
    #             if access_score.earned==0:
    #                 self.logger.warning('FsF-A1-01M : No rights information is available in metadata')
    #                 access_result.test_status = "fail"
    #                 access_score.earned = 0
    #         else:
    #             self.logger.warning('FsF-A1-01M : No rights or licence information is included in metadata')
    #     access_result.score=access_score
    #     access_result.output=access_output
    #     if self.isDebug:
    #         access_result.test_debug = self.msg_filter.getMessage(access_identifier)
    #     return access_result.to_dict()

    def check_license(self):
        self.count += 1
        license_identifier = 'FsF-R1.1-01M'  # FsF-R1.1-01M: Data Usage Licence
        license_mname = FAIRCheck.METRICS.get(license_identifier).get('metric_name')
        license_sc = int(FAIRCheck.METRICS.get(license_identifier).get('total_score'))
        license_score = FAIRResultCommonScore(total=license_sc)
        license_result = License(id=self.count, metric_identifier=license_identifier, metric_name=license_mname)
        licenses_list = []
        specified_licenses = self.metadata_merged.get('license')
        if specified_licenses is not None:
            if isinstance(specified_licenses, str):  # licenses maybe string or list depending on metadata schemas
                specified_licenses = [specified_licenses]
            for l in specified_licenses:
                license_output = LicenseOutputInner()
                license_output.license = l
                isurl = idutils.is_url(l)
                if isurl:
                    spdx_html, spdx_osi = self.lookup_license_by_url(l, license_identifier)
                else:  # maybe licence name
                    spdx_html, spdx_osi = self.lookup_license_by_name(l, license_identifier)
                if not spdx_html:
                    self.logger.warning('FsF-R1.1-01M : No SPDX license representation (spdx url, osi_approved) found')
                license_output.details_url = spdx_html
                license_output.osi_approved = spdx_osi
                licenses_list.append(license_output)
            license_result.test_status = "pass"
            license_score.earned = license_sc
        else:
            license_score.earned = 0
            self.logger.warning('FsF-R1.1-01M : No license information is included in metadata')
        license_result.output = licenses_list
        license_result.score = license_score

        if self.isDebug:
            license_result.test_debug = self.msg_filter.getMessage(license_identifier)
        return license_result.to_dict()

    def lookup_license_by_url(self, u, metric_id):
        self.logger.info('{0} : Search license SPDX details by url - {1}'.format(metric_id, u))
        html_url = None
        isOsiApproved = False
        for item in FAIRCheck.SPDX_LICENSES:
            # u = u.lower()
            # if any(u in v.lower() for v in item.values()):
            seeAlso = item['seeAlso']
            if any(u in v for v in seeAlso):
                self.logger.info('{0} : Found SPDX license representation - {1}'.format(metric_id, item['detailsUrl']))
                # html_url = '.html'.join(item['detailsUrl'].rsplit('.json', 1))
                html_url = item['detailsUrl'].replace(".json", ".html")
                isOsiApproved = item['isOsiApproved']
                break
        return html_url, isOsiApproved

    def lookup_license_by_name(self, lvalue, metric_id):
        # TODO - find simpler way to run fuzzy-based search over dict/json (e.g., regex)
        html_url = None
        isOsiApproved = False
        self.logger.info('{0} : Search license SPDX details by name - {1}'.format(metric_id, lvalue))
        # Levenshtein distance similarity ratio between two license name
        sim = [Levenshtein.ratio(lvalue.lower(), i) for i in FAIRCheck.SPDX_LICENSE_NAMES]
        if max(sim) > 0.85:
            index_max = max(range(len(sim)), key=sim.__getitem__)
            sim_license = FAIRCheck.SPDX_LICENSE_NAMES[index_max]
            found = next((item for item in FAIRCheck.SPDX_LICENSES if item['name'] == sim_license), None)
            self.logger.info('FsF-R1.1-01M: Found SPDX license representation - {}'.format(found['detailsUrl']))
            # html_url = '.html'.join(found['detailsUrl'].rsplit('.json', 1))
            html_url = found['detailsUrl'].replace(".json", ".html")
            isOsiApproved = found['isOsiApproved']
        return html_url, isOsiApproved

    def check_relatedresources(self):
        self.count += 1
        related_identifier = 'FsF-I3-01M'  # FsF-I3-01M: Meaningful links to related entities
        related_mname = FAIRCheck.METRICS.get(related_identifier).get('metric_name')
        related_sc = int(FAIRCheck.METRICS.get(related_identifier).get('total_score'))
        related_score = FAIRResultCommonScore(total=related_sc)
        related_result = RelatedResource(id=self.count, metric_identifier=related_identifier, metric_name=related_mname)
        related_output = IdentifierIncludedOutput()

        #if self.metadata_merged.get('related_resources'):
        if self.related_resources: #TODO include source of relation
            related_output = self.related_resources
            related_result.test_status = 'pass'
            related_score.earned = related_sc

        related_result.score = related_score
        related_result.output = related_output
        if self.isDebug:
            related_result.test_debug = self.msg_filter.getMessage(related_identifier)
        return related_result.to_dict()

    def check_searchable(self):
        self.count += 1
        searchable_identifier = 'FsF-F4-01M'  # FsF-F4-01M: Searchable metadata
        searchable_name = FAIRCheck.METRICS.get(searchable_identifier).get('metric_name')
        searchable_result = Searchable(id=self.count, metric_identifier=searchable_identifier, metric_name=searchable_name)
        searchable_sc = int(FAIRCheck.METRICS.get(searchable_identifier).get('total_score'))
        searchable_score = FAIRResultCommonScore(total=searchable_sc)
        searchable_output = SearchableOutput()
        search_mechanisms = []
        sources_registry = [MetaDataCollector.Sources.SCHEMAORG_NEGOTIATE.value,
                            MetaDataCollector.Sources.DATACITE_JSON.value]
        all = str([e.value for e in MetaDataCollector.Sources]).strip('[]')
        self.logger.info('FsF-F4-01M : Supported metadata retrieval/extraction - {}'.format(all))
        search_engines_support = [MetaDataCollector.Sources.SCHEMAORG_EMBED.value,
                                  MetaDataCollector.Sources.DUBLINCORE.value,
                                  MetaDataCollector.Sources.SIGN_POSTING.value]
        # Check search mechanisms based on sources of metadata extracted.
        search_engine_support_match: List[Any] = list(set(self.metadata_sources).intersection(search_engines_support))
        if search_engine_support_match:
            search_mechanisms.append(
                OutputSearchMechanisms(mechanism='structured data', mechanism_info=search_engine_support_match))
        else:
            self.logger.warning('FsF-F4-01M : Metadata NOT found through - {}'.format(search_engines_support))

        registry_support_match = list(set(self.metadata_sources).intersection(sources_registry))
        if registry_support_match:
            search_mechanisms.append(
                OutputSearchMechanisms(mechanism='metadata registry', mechanism_info=registry_support_match))
        else:
            self.logger.warning('FsF-F4-01M : Metadata NOT found through - {}'.format(sources_registry))
        # TODO (Important) - search via b2find
        length = len(search_mechanisms)
        if length > 0:
            searchable_result.test_status = 'pass'
            if length == 2:
                searchable_score.earned = searchable_sc
            if length == 1:
                searchable_score.earned = searchable_sc - 1
            searchable_result.score = searchable_score
            searchable_output.search_mechanisms = search_mechanisms
            searchable_result.output = searchable_output
        else:
            self.logger.warning('No search mechanism supported')

        if self.isDebug:
            searchable_result.test_debug = self.msg_filter.getMessage(searchable_identifier)
        return searchable_result.to_dict()

    def check_data_file_format(self):
        #open_formats=['image/apng','text/csv','application/json']
        #TODO: add xml txt csv
        text_format_regex=r'(^text)[\/]|[\/\+](xml|text|json)'
        self.count += 1
        data_file_format_identifier = 'FsF-R1.3-02D'
        data_file_format_name = FAIRCheck.METRICS.get(data_file_format_identifier).get('metric_name')
        data_file_format_sc = int(FAIRCheck.METRICS.get(data_file_format_identifier).get('total_score'))
        data_file_format_score = FAIRResultCommonScore(total=data_file_format_sc)
        data_file_format_result = DataFileFormat(id=self.count, metric_identifier=data_file_format_identifier, metric_name=data_file_format_name)
        data_file_format_output = DataFileFormatOutput()
        data_file_list=[]
        data_file_format_result.score = 0
        if len(self.content_identifier) > 0:
            self.logger.info('FsF-R1.3-02D : Found some object content identifiers')
            for data_file in self.content_identifier:
                data_file_output = DataFileFormatOutputInner()
                preferance_reason=[]
                subject_area=[]
                mime_type=data_file.get('type')
                #TODO: change output type instead of is_long_term_format etc use:
                # is_prefered_format: boolean
                # type: ['long term format','science format']
                # domain: list of scientific domains, default: 'General'
                if mime_type is None or mime_type in ['application/octet-stream']:
                    # if mime type not given try to guess it based on the file name
                    guessed_mime_type=mimetypes.guess_type(data_file.get('url'))
                    mime_type=guessed_mime_type[0]
                if mime_type is not None:
                    # FILE FORMAT CHECKS....
                    # check if format is a scientific one:
                    if mime_type in FAIRCheck.SCIENCE_FILE_FORMATS:
                        if FAIRCheck.SCIENCE_FILE_FORMATS.get(mime_type) == 'Generic':
                            subject_area.append('General')
                            preferance_reason.append('generic science format')
                        else:
                            subject_area.append(FAIRCheck.SCIENCE_FILE_FORMATS.get(mime_type))
                            preferance_reason.append('science format')
                        data_file_output.is_preferred_format= True
                        data_file_format_result.test_status = 'pass'

                    # check if long term format
                    if mime_type in FAIRCheck.LONG_TERM_FILE_FORMATS:
                        preferance_reason.append('long term format')
                        subject_area.append('General')
                        data_file_output.is_preferred_format = True
                        data_file_format_result.test_status = 'pass'

                    #TODO: check if open format
                    if mime_type in FAIRCheck.OPEN_FILE_FORMATS:
                        preferance_reason.append('open format')
                        subject_area.append('General')
                        data_file_output.is_preferred_format = True
                        data_file_format_result.test_status = 'pass'

                    data_file_output.mime_type=mime_type
                    data_file_output.file_uri=data_file.get('url')
                    data_file_list.append(data_file_output)
                    #generic text/xml/json file check
                    if re.search(text_format_regex,mime_type):
                        preferance_reason.extend(['long term format','open format','generic science format'])
                        subject_area.append('General')
                        data_file_output.is_preferred_format= True
                        data_file_format_result.test_status = 'pass'

                if data_file_format_result.test_status == 'pass':
                    data_file_format_result.score = 1
                data_file_output.preference_reason=preferance_reason
                data_file_output.subject_areas=subject_area

                    #if mime_type in open_formats:

        else:
            self.logger.info('FsF-R1.3-02D : Could not perform file format checks, no object content identifiers available')
            data_file_format_result.test_status='fail'

        data_file_format_output=data_file_list
        data_file_format_result.output = data_file_format_output
        if self.isDebug:
            data_file_format_result.test_debug = self.msg_filter.getMessage(data_file_format_identifier)

        return data_file_format_result.to_dict()

    def check_community_metadatastandards(self):
        self.count += 1
        communitystd_identifier = 'FsF-R1.3-01M'  # FsF-R1.3-01M: Community-endorsed metadata
        communitystd_name = FAIRCheck.METRICS.get(communitystd_identifier).get('metric_name')
        communitystd_result = Searchable(id=self.count, metric_identifier=communitystd_identifier, metric_name=communitystd_name)
        communitystd_sc = int(FAIRCheck.METRICS.get(communitystd_identifier).get('total_score'))
        communitystd_score = FAIRResultCommonScore(total=communitystd_sc)

        standards_detected: List[CommunityEndorsedStandardOutputInner] = []
        if self.community_standards:
            for s in self.community_standards:
                standard_found = self.lookup_metadatastandard_by_name(s)
                if standard_found:
                    subject = FAIRCheck.COMMUNITY_STANDARDS.get(standard_found).get('subject_areas')
                    if subject and all(elem == "Multidisciplinary" for elem in subject):
                        self.logger.info('FsF-R1.3-01M : Skipping non-disciplinary standard listed in OAIPMH - {}'.format(s))
                    else:
                        out = CommunityEndorsedStandardOutputInner()
                        out.metadata_standard = s
                        out.subject_areas = FAIRCheck.COMMUNITY_STANDARDS.get(standard_found).get('subject_areas')
                        out.urls = FAIRCheck.COMMUNITY_STANDARDS.get(standard_found).get('urls')
                        standards_detected.append(out)

        if not standards_detected and self.community_standards_uri:
        #use schems declared in oai-pmh end point instead
            self.logger.info(
                '{} : Metadata standards defined in OAI-PMH endpoint - {}'.format('FsF-R1.3-01M', self.community_standards_uri.keys()))
            for k,v in self.community_standards_uri.items():
                out = CommunityEndorsedStandardOutputInner()
                out.metadata_standard = k
                out.urls = v
                standards_detected.append(out)

        if standards_detected:
            communitystd_score.earned = communitystd_sc
            communitystd_result.test_status = 'pass'
        else:
            self.logger.warning('FsF-R1.3-01M : Unable to determine community standard')

        communitystd_result.score = communitystd_score
        communitystd_result.output = standards_detected
        if self.isDebug:
            communitystd_result.test_debug = self.msg_filter.getMessage(communitystd_identifier)
        return communitystd_result.to_dict()

    def lookup_metadatastandard_by_name(self, value):
        found = None
        # get standard name with the highest matching percentage using fuzzywuzzy
        highest = process.extractOne(value, FAIRCheck.COMMUNITY_STANDARDS_NAMES, scorer=fuzz.token_sort_ratio)
        if highest[1] > 80:
            found = highest[0]
        return found

    def check_data_provenance(self):
        data_provenance_identifier = 'FsF-R1.2-01M'
        data_provenance_name = FAIRCheck.METRICS.get(data_provenance_identifier).get('metric_name')
        data_provenance_sc = int(FAIRCheck.METRICS.get(data_provenance_identifier).get('total_score'))
        data_provenance_score = FAIRResultCommonScore(total=data_provenance_sc)
        data_provenance_result = DataProvenance(id=self.count, metric_identifier=data_provenance_identifier,
                                                 metric_name=data_provenance_name)
        data_provenance_output = DataProvenanceOutput()
        data_provenance_score=0
        has_creation_provenance = False
        provenance_elements = []
        provenance_namespaces=['http://www.w3.org/ns/prov#','http://purl.org/pav/']
        provenance_status = 'fail'
        creation_metadata_output = DataProvenanceOutputInner()
        creation_metadata_output.provenance_metadata = []
        creation_metadata_output.is_available = False

        #creation info
        if 'title' in self.metadata_merged:
            creation_metadata_output.provenance_metadata.append({'title' : self.metadata_merged['title']})
            if 'publication_date' in self.metadata_merged or 'creation_date' in self.metadata_merged:
                if 'creation_date' in self.metadata_merged:
                    creation_metadata_output.provenance_metadata.append({'creation_date' : self.metadata_merged['creation_date']})
                else:
                    creation_metadata_output.provenance_metadata.append({'publication_date' : self.metadata_merged['publication_date']})
                if 'creator' in self.metadata_merged or 'contributor' in self.metadata_merged:
                    creation_metadata_output.is_available=True
                    if 'creator' in self.metadata_merged:
                        creation_metadata_output.provenance_metadata.append({'creator' : self.metadata_merged['creator'][0]})
                    else:
                        creation_metadata_output.provenance_metadata.append({'contributor' : self.metadata_merged['contributor'][0]})
                provenance_status = 'pass'
                self.logger.info('FsF-R1.2-01M : Found basic creation-related provenance information')
                data_provenance_score=data_provenance_score+0.5
        data_provenance_output.creation_provenance_included=creation_metadata_output

        #modification versioning info
        modified_indicators=['modified_date','version']
        modified_intersect=list(set(modified_indicators).intersection(self.metadata_merged))
        modified_metadata_output = DataProvenanceOutputInner()
        modified_metadata_output.provenance_metadata = []
        modified_metadata_output.is_available = False
        if len(modified_intersect)>0:
            self.logger.info('FsF-R1.2-01M : Found basic versioning-related provenance information')
            modified_metadata_output.is_available = True
            for modified_element in modified_intersect:
                modified_metadata_output.provenance_metadata.append({modified_element: self.metadata_merged[modified_element]})
            provenance_status = 'pass'
            data_provenance_score = data_provenance_score+0.5
        data_provenance_output.modification_provenance_included = modified_metadata_output

        #process, origin derved from relations
        process_indicators=['isVersionOf', 'isBasedOn', 'isFormatOf', 'IsNewVersionOf',
                            'IsVariantFormOf', 'IsDerivedFrom', 'Obsoletes']
        relations_metadata_output = DataProvenanceOutputInner()
        relations_metadata_output.provenance_metadata = []
        relations_metadata_output.is_available = False
        if 'related_resources' in self.metadata_merged:
            has_relations=False
            for rr in self.metadata_merged['related_resources']:
                if rr.get('relation_type') in process_indicators:
                    has_relations=True
                    relations_metadata_output.provenance_metadata.append({rr.get('relation_type') : rr.get('related_resource')})
            if has_relations:
                relations_metadata_output.is_available = True
                data_provenance_score = data_provenance_score + 0.5
                self.logger.info('FsF-R1.2-01M : Found basic process-related provenance information')
        data_provenance_output.provenance_relations_included = relations_metadata_output

        #structured provenance metadata available
        structured_metadata_output = DataProvenanceOutputInner()
        structured_metadata_output.provenance_metadata = []
        structured_metadata_output.is_available = False
        used_provenance_namespace = list(set(provenance_namespaces).intersection(set(self.namespace_uri)))
        if used_provenance_namespace:
            data_provenance_score = data_provenance_score + 0.5
            structured_metadata_output.is_available = True
            for used_prov_ns in used_provenance_namespace:
                structured_metadata_output.provenance_metadata.append({'namespace': used_prov_ns})
            self.logger.info('FsF-R1.2-01M : Found use of dedicated provenance ontologies')
        data_provenance_output.structured_provenance_available = structured_metadata_output

        data_provenance_result.test_status=provenance_status
        data_provenance_result.score = data_provenance_score
        data_provenance_result.output = data_provenance_output

        return data_provenance_result.to_dict()

    def check_data_content_metadata(self):
        #initially verification is restricted to the first file:
        data_content_metadata_identifier = 'FsF-R1-01MD'
        data_content_metadata_name = FAIRCheck.METRICS.get(data_content_metadata_identifier).get('metric_name')
        data_content_metadata_sc = int(FAIRCheck.METRICS.get(data_content_metadata_identifier).get('total_score'))
        data_content_metadata_score = FAIRResultCommonScore(total=data_content_metadata_sc)
        data_content_metadata_result = DataContentMetadata(id=self.count, metric_identifier=data_content_metadata_identifier,
                                                metric_name=data_content_metadata_name)
        data_content_metadata_output = DataContentMetadataOutput()
        data_content_metadata_result.score = 0
        data_content_metadata_output.data_content_descriptor=[]
        if 'measured_variable' in self.metadata_merged:
            self.logger.info('FsF-R1-01MD : Found measured variables as content descriptor')
            data_content_metadata_result.score = 1
            data_content_metadata_result.test_status = 'pass'
            data_content_metadata_output.has_content_descriptors= True
            for variable in self.metadata_merged['measured_variable']:
                data_content_metadata_inner = DataContentMetadataOutputInner()
                data_content_metadata_inner.descriptor_name=variable
                data_content_metadata_inner.descriptor_type='measured_variable'
                if variable in self.test_data_content_text:
                    data_content_metadata_inner.matchescontent = True
                    data_content_metadata_result.score = 2
                data_content_metadata_output.data_content_descriptor.append(data_content_metadata_inner)

        data_content_metadata_result.output=data_content_metadata_output

        return data_content_metadata_result.to_dict()

    def check_formal_metadata(self):
        self.count += 1
        formal_meta_identifier = 'FsF-I1-01M'
        formal_meta_name = FAIRCheck.METRICS.get(formal_meta_identifier).get('metric_name')
        formal_meta_sc = int(FAIRCheck.METRICS.get(formal_meta_identifier).get('total_score'))
        formal_meta_score = FAIRResultCommonScore(total=formal_meta_sc)
        formal_meta_result = DataProvenance(id=self.count, metric_identifier=formal_meta_identifier, metric_name=formal_meta_name)

        outputs = []
        score = 0
        test_status = 'fail'
        search_values = [self.pid_url, self.landing_url, self.metadata_merged.get('title')]
        search_values= [str(x) for x in search_values if x is not None]
        # note: 'source' allowed values = ["typed_link", "content_negotiate", "structured_data", "sparql_endpoint"]

        #1. light-weight check (structured_data), expected keys from extruct ['json-ld','rdfa']
        self.logger.info('{0} : Check of structured data (RDF serialization) embedded in the data page'.format(formal_meta_identifier))
        if MetaDataCollector.Sources.SCHEMAORG_EMBED.value in self.metadata_sources:
            outputs.append(FormalMetadataOutputInner(serialization_format='JSON-LD', source='structured_data', is_metadata_found=True))
            self.logger.info('{0} : RDF Serialization found in the data page - {1}'.format(formal_meta_identifier, 'JSON-LD'))
            score += 1
        else:
            if self.extruct:
                if 'rdfa' in self.extruct.keys():
                    self.logger.info('{0} : RDF Serialization found in the data page - {1}'.format(formal_meta_identifier, 'RDFa'))
                    self.logger.info('{0} : Searching \'proxy\' values in RDFa representation - {1}'.format(formal_meta_identifier, search_values))
                    rdfa_doc = str(self.extruct.get('rdfa')).lower()
                    for s in search_values:
                        #  takes in the shortest string (s) and the matches with all substrings of the other string (rdfa_doc)
                        partial_ratio = fuzz.partial_ratio(s.lower(), rdfa_doc)
                        if partial_ratio > 70: # heuristic score
                            self.logger.info('{0} : RDFa document seems to represent the data object, proxy found'.format(formal_meta_identifier))
                            outputs.append(FormalMetadataOutputInner(serialization_format='RDFa', source='structured_data', is_metadata_found=True))
                            score += 1
                            break
        if len(outputs)==0:
            self.logger.info('{0} : NO structured data (RDF serialization) embedded in the data page'.format(formal_meta_identifier))

        # 2. hard check (typed-link, content negotiate, sparql endpoint)
        # 2a. in the object page, you may find a <link rel="alternate" type="application/rdf+xml" … />
        # 2b.content negotiate
        formalExists = False
        self.logger.info('{0} : Check if RDF-based typed link included'.format(formal_meta_identifier))
        if MetaDataCollector.Sources.RDF_SIGN_POSTING.value in self.metadata_sources:
            contenttype = self.rdf_collector.get_content_type()
            self.logger.info('{0} : RDF graph retrieved, content type - {1}'.format(formal_meta_identifier, contenttype))
            outputs.append(FormalMetadataOutputInner(serialization_format=contenttype, source='typed_link', is_metadata_found=True))
            score += 1
            formalExists = True
        else:
            self.logger.info('{0} : NO RDF-based typed link found'.format(formal_meta_identifier))
            self.logger.info('{0} : Check if RDF metadata available through content negotiation'.format(formal_meta_identifier))
            if MetaDataCollector.Sources.LINKED_DATA.value in self.metadata_sources:
                contenttype = self.rdf_collector.get_content_type()
                self.logger.info(
                    '{0} : RDF graph retrieved, content type - {1}'.format(formal_meta_identifier, contenttype))
                outputs.append(FormalMetadataOutputInner(serialization_format=contenttype, source='content_negotiate',
                                                         is_metadata_found=True))
                score += 1
                formalExists = True
            else:
                self.logger.info('{0} : NO RDF metadata available through content negotiation'.format(formal_meta_identifier))

        # 2c. try to retrieve via sparql endpoint (if available)
        if not formalExists:
            self.logger.info('{0} : Check if SPARQL endpoint is available'.format(formal_meta_identifier))
            # self.sparql_endpoint = 'http://data.archaeologydataservice.ac.uk/sparql/repositories/archives' #test endpoint
            # self.sparql_endpoint = 'http://data.archaeologydataservice.ac.uk/query/' #test web sparql form
            # self.pid_url = 'http://data.archaeologydataservice.ac.uk/10.5284/1000011' #test uri
            # self.sparql_endpoint = 'https://meta.icos-cp.eu/sparqlclient/' #test endpoint
            # self.pid_url = 'https://meta.icos-cp.eu/objects/9ri1elaogsTv9LQFLNTfDNXm' #test uri
            if self.sparql_endpoint:
                self.logger.info('{0} : SPARQL endpoint found - {1}'.format(formal_meta_identifier, self.sparql_endpoint))
                sparql_provider = SPARQLMetadataProvider(endpoint=self.sparql_endpoint, logger=self.logger,metric_id=formal_meta_identifier)
                query = "CONSTRUCT {{?dataURI ?property ?value}} where {{ VALUES ?dataURI {{ <{}> }} ?dataURI ?property ?value }}".format(self.pid_url)
                self.logger.info('{0} : Executing SPARQL - {1}'.format(formal_meta_identifier, query))
                rdfgraph, contenttype = sparql_provider.getMetadata(query)
                if rdfgraph:
                    outputs.append(
                        FormalMetadataOutputInner(serialization_format=contenttype, source='sparql_endpoint', is_metadata_found=True))
                    score += 1
                    self.namespace_uri.extend(sparql_provider.getNamespaces())
                else:
                    self.logger.warning('{0} : NO RDF metadata retrieved through the sparql endpoint'.format(formal_meta_identifier))
            else:
                self.logger.warning('{0} : No SPARQL endpoint found through re3data based on the object URI provided'.format(formal_meta_identifier))

        if score > 0:
            test_status = 'pass'
        formal_meta_result.test_status = test_status
        formal_meta_score.earned = score
        formal_meta_result.score = formal_meta_score
        formal_meta_result.output = outputs
        if self.isDebug:
            formal_meta_result.test_debug = self.msg_filter.getMessage(formal_meta_identifier)
        return formal_meta_result.to_dict()

    def check_semantic_vocabulary(self):
        self.count += 1
        semanticvocab_identifier = 'FsF-I1-02M'
        semanticvocab_name = FAIRCheck.METRICS.get(semanticvocab_identifier).get('metric_name')
        semanticvocab_sc = int(FAIRCheck.METRICS.get(semanticvocab_identifier).get('total_score'))
        semanticvocab_score = FAIRResultCommonScore(total=semanticvocab_sc)
        semanticvocab_result = DataProvenance(id=self.count, metric_identifier=semanticvocab_identifier, metric_name=semanticvocab_name)

        #remove duplicates
        self.namespace_uri = list(set(self.namespace_uri))
        # filter out common namespaces, starts with
        self.namespace_uri = [x for x in self.namespace_uri if not x.startswith('http://www.w3.org')] #TODO whitelist
        self.logger.info('{0} : Number of namespaces included in all RDF-based metadata - {1}'.format(semanticvocab_identifier, len(self.namespace_uri)))

        print(self.namespace_uri)
        # cross check with linked data cloud list

        if self.isDebug:
            semanticvocab_result.test_debug = self.msg_filter.getMessage(semanticvocab_identifier)
        return semanticvocab_result.to_dict()

