# -*- coding: utf-8 -*-
import logging
import re
import urllib
import urllib.request as urllib
from urllib.parse import urlparse

import Levenshtein
import idutils
from fuji_server.helper.log_message_filter import MessageFilter
from fuji_server.helper.metadata_collector_datacite import MetaDataCollectorDatacite
from fuji_server.helper.metadata_collector_dublincore import MetaDataCollectorDublinCore
from fuji_server.helper.metadata_collector_schemaorg import MetaDataCollectorSchemaOrg
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.metadata_harvester_oai import OAIMetadataHarvesters
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.repository_helper import RepositoryHelper
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from fuji_server.models import *
from fuji_server.models import CoreMetadataOutput


class FAIRCheck:

    METRICS = None
    SPDX_LICENSES = None
    SPDX_LICENSE_NAMES = None

    def __init__(self, uid, oai=None, test_debug=False):
        self.id = uid
        self.oaipmh_endpoint = oai
        self.pid_url = None  # full pid # e.g., "https://doi.org/10.1594/pangaea.906092 or url (non-pid)
        self.landing_url = None  # url of the landing page of self.pid_url
        self.landing_html = None
        self.landing_origin = None #schema + authority of the landing page e.g. https://www.pangaea.de
        self.pid_scheme = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metadata_sources = []
        self.isDebug = test_debug
        self.metadata_merged = {}
        self.reference_elements = Mapper.REFERENCE_METADATA_LIST.value.copy() # all metadata elements required for FUJI metrics
        if self.isDebug:
            self.msg_filter = MessageFilter()
            self.logger.addFilter(self.msg_filter)
            self.logger.setLevel(logging.INFO) # set to debug in testing environment
        self.oaipmh_harvester = None
        FAIRCheck.load_predata()

    @classmethod
    def load_predata(cls):
        if not cls.METRICS:
            cls.METRICS = Preprocessor.get_custom_metrics(['metric_name', 'total_score'])
        if not cls.SPDX_LICENSES:
            #cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES, cls.SPDX_LICENSE_URLS = Preprocessor.get_licenses()
            cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES = Preprocessor.get_licenses()
        #if not cls.DATACITE_REPOSITORIES:
            #cls.DATACITE_REPOSITORIES = Preprocessor.getRE3repositories()

    @staticmethod
    def uri_validator(u): #TODO integrate into request_helper.py
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
        uid_result = Uniqueness(id=1, metric_identifier=uid_metric_identifier, metric_name=uid_metric_name)
        pid_result = Persistence(id=2, metric_identifier=pid_metric_identifier, metric_name=pid_metric_name)
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
            requestHelper.setAcceptType(AcceptTypes.html) # request
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
                    pid_output.resolved_url = self.landing_url # url is active, although the identifier is not based on a pid scheme
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

    def retrieve_metadata (self, extruct_metadata):
        if extruct_metadata:
            embedded_exists = [k for k, v in extruct_metadata.items() if v]
            self.logger.info('FsF-F2-01M : Formats of structured metadata embedded in HTML markup {}'.format(embedded_exists))
            if embedded_exists: # retrieve metadata from landing page
                self.retrieve_metadata_embedded(extruct_metadata)
        else:
            self.logger.warning('FsF-F2-01M : No structured metadata embedded in HTML')

        if self.reference_elements: # this will be always true as we need datacite client id
            self.retrieve_metadata_external()
        self.logger.info('FsF-F2-01M : Type of object described by the metadata - {}'.format(self.metadata_merged.get('object_type')))

        # retrieve re3metadata based on pid specified
        self.retrieve_re3data()

        # validate and instatiate oai-pmh harvester if the endpoint is valie
        if self.oaipmh_endpoint:
            if (self.uri_validator(self.oaipmh_endpoint)) and self.pid_url:
                self.oaipmh_harvester = OAIMetadataHarvesters(endpoint=self.oaipmh_endpoint, resourceidentifier=self.pid_url)

    def retrieve_re3data(self):
        client_id = self.metadata_merged.get('datacite_client')
        if client_id and self.pid_scheme:
            repoHelper = RepositoryHelper(client_id, self.pid_scheme)
            repoHelper.lookup_re3data()

    def retrieve_metadata_embedded(self, extruct_metadata):
       # ========= retrieve schema.org (embedded, or from via content-negotiation if pid provided) =========
        isPid = False
        if self.pid_scheme:
            isPid = True
        ext_meta = extruct_metadata.get('json-ld')
        schemaorg_collector = MetaDataCollectorSchemaOrg(loggerinst=self.logger, sourcemetadata=ext_meta, mapping=Mapper.SCHEMAORG_MAPPING,
                                       ispid=isPid, pidurl=self.pid_url)
        source_schemaorg, schemaorg_dict = schemaorg_collector.parse_metadata()
        if schemaorg_dict:
            not_null_sco = [k for k, v in schemaorg_dict.items() if v is not None]
            self.metadata_sources.append(source_schemaorg)
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
            source_dc, dc_dict= dc_collector.parse_metadata()
            if dc_dict:
                not_null_dc = [k for k, v in dc_dict.items() if v is not None]
                self.metadata_sources.append(source_dc)
                for d in not_null_dc:
                    if d in self.reference_elements:
                        self.metadata_merged[d] = dc_dict[d]
                        self.reference_elements.remove(d)
            else:
                self.logger.info('FsF-F2-01M : DublinCore metadata UNAVAILABLE')

        # ========= retrieve typed links =========
        if self.metadata_merged.get('object_content_identifier') is None:
            links = self.get_html_typed_links()
            if links:
                self.metadata_merged ['object_content_identifier'] = self.get_html_typed_links()
                self.metadata_sources.append(MetaDataCollector.Sources.SIGN_POSTING.value)


    # TODO (important) separate class to represent https://www.iana.org/assignments/link-relations/link-relations.xhtml
    #  use IANA relations for extracting metadata and meaningful links
    # TODO (important) - https://signposting.org/publication_boundary/, create a dict of {'href':URL,'format':FORMAT, 'rel':REL, 'type':TYPE}
    def get_html_typed_links(self):
        # Use Typed Links in HTTP Link headers to help machines find the resources that make up a publication.
        # <link rel="item" href="https://doi.pangaea.de/10.1594/PANGAEA.906092?format=zip" type="application/zip">
        datalinks = []
        reg_item = '<link rel\s*=\s*\"(item)\"(.*?)href\s*=\s*\"(.*?)\"'
        if self.landing_html != None:
            header_links_matches = re.findall(reg_item, self.landing_html) # ('item', ' ', 'https://doi.pangaea.de/10.1594/PANGAEA.906092?format=zip')
            if len(header_links_matches) > 0:
                for datalink in header_links_matches:
                    datalinks.append(datalink[2])
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
                for r in not_null_dcite:
                    if r in self.reference_elements:
                        self.metadata_merged[r] = dcitejsn_dict[r]
                        self.reference_elements.remove(r)
            else:
                self.logger.info('FsF-F2-01M : Datacite metadata UNAVAILABLE')
        else:
            self.logger.info('FsF-F2-01M : Not a PID, therefore Datacite metadata (json) not requested.')

        if self.reference_elements:
            self.logger.debug('Reference metadata elements NOT FOUND - {}'.format(self.reference_elements))
            # TODO (Important) - search via b2find
            # TODO (IMPORTANT!) -  try some content negotiation (rdf) + update self.self.metadata_merged
            # self.rdf_graph = self.content_negotiate('rdf','FsF-F2-01M')
        else:
            self.logger.debug('FsF-F2-01M : ALL reference metadata elements available')

    def check_minimal_metatadata(self):
        coremeta_identifier = 'FsF-F2-01M'
        meta_sc = int(FAIRCheck.METRICS.get(coremeta_identifier).get('total_score'))
        meta_score = FAIRResultCommonScore(total=meta_sc)
        coremeta_name = FAIRCheck.METRICS.get(coremeta_identifier).get('metric_name')
        meta_result = CoreMetadata(id=3, metric_identifier=coremeta_identifier, metric_name=coremeta_name)

        metadata_required = Mapper.REQUIRED_CORE_METADATA.value
        metadata_found = {k: v for k, v in self.metadata_merged.items() if k in metadata_required}
        self.logger.info('FsF-F2-01M : Required core metadata {}'.format(metadata_required))
        partial_elements = ['creator', 'title', 'object_identifier', 'publication_date']
        if set(metadata_found) == set(metadata_required):
            metadata_status = 'all metadata'
            meta_score.earned = meta_sc
            test_status = 'pass'
        #elif 1 <= len_found_metadata < len_metadata_required: #TODO - determine the threshold between partial and zero
        elif set(partial_elements).issubset(metadata_found):
            metadata_status = 'partial metadata'
            meta_score.earned = meta_sc - 1
            test_status = 'pass'
        else:
            metadata_status = 'no metadata'
            meta_score.earned = 0
            test_status = 'fail'

        missing = list(set(metadata_required) - set(metadata_found))
        if missing:
            self.logger.warning('FsF-F2-01M : Missing core metadata %s' %(missing))

        meta_output: CoreMetadataOutput = CoreMetadataOutput(core_metadata_status=metadata_status, core_metadata_source=self.metadata_sources)
        meta_output.core_metadata_found = metadata_found
        meta_result.test_status = test_status
        meta_result.score = meta_score
        meta_result.output = meta_output
        if self.isDebug:
            meta_result.test_debug = self.msg_filter.getMessage(coremeta_identifier)
        return meta_result.to_dict()


    def check_content_identifier_included(self):
        did_included_identifier = 'FsF-F3-01M'  # FsF-F3-01M: Inclusion of data identifier in metadata
        included_name = FAIRCheck.METRICS.get(did_included_identifier).get('metric_name')
        did_result = IdentifierIncluded(id=4, metric_identifier=did_included_identifier, metric_name=included_name)
        did_sc = int(FAIRCheck.METRICS.get(did_included_identifier).get('total_score'))
        did_score = FAIRResultCommonScore(total=did_sc)
        did_output = IdentifierIncludedOutput()

        id_object = self.metadata_merged.get('object_identifier')
        did_output.object_identifier_included = id_object
        contents = self.metadata_merged.get('object_content_identifier')
        self.logger.info('FsF-F3-01M : Data object identifier specified {}'.format(id_object))

        if FAIRCheck.uri_validator(id_object): # TODO: check if specified identifier same is provided identifier (handle pid and non-pid cases)
            did_score.earned = did_sc
            did_result.test_status = "pass"
        else:
            self.logger.warning('FsF-F3-01M : Malformed Identifier!')

        content_list=[]
        if contents:
            for content_id in contents:
                self.logger.info('FsF-F3-01M : Data object (content) identifier included {}'.format(content_id))
                did_output_content = IdentifierIncludedOutputInner()
                did_output_content.content_identifier_included = content_id
                try:
                    urllib.urlopen(content_id) # only check the status, do not download the content
                except urllib.HTTPError as e:
                    self.logger.warning('FsF-F3-01M : Content identifier {0}, HTTPError code {1} '.format(content_id, e.code))
                except urllib.URLError as e:
                    self.logger.exception(e.reason)
                else: # will be executed if there is no exception
                    did_output_content.content_identifier_active = True
                    content_list.append(did_output_content)
        else:
            self.logger.warning('FsF-F3-01M : Data (content) identifier is missing.')
        did_output.content = content_list
        did_result.output = did_output
        did_result.score = did_score

        if self.isDebug:
            did_result.test_debug = self.msg_filter.getMessage(did_included_identifier)
        return did_result.to_dict()

    def check_license(self):
        license_identifier = 'FsF-R1.1-01M'  # FsF-R1.1-01M: Data Usage Licence
        license_mname = FAIRCheck.METRICS.get(license_identifier).get('metric_name')
        license_sc = int(FAIRCheck.METRICS.get(license_identifier).get('total_score'))
        license_score = FAIRResultCommonScore(total=license_sc)
        license_result = License(id=12, metric_identifier=license_identifier, metric_name=license_mname)
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
                    spdx_html, spdx_osi = self.lookup_license_by_url(l)
                else:  # maybe licence name
                    spdx_html, spdx_osi = self.lookup_license_by_name(l)
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

    def lookup_license_by_url(self, u):
        self.logger.info('FsF-R1.1-01M : Search license SPDX details by licence url - {}'.format(u))
        html_url = None
        isOsiApproved = False
        for item in FAIRCheck.SPDX_LICENSES:
            #u = u.lower()
            #if any(u in v.lower() for v in item.values()):
            seeAlso = item['seeAlso']
            if any(u in v for v in seeAlso):
                self.logger.info('FsF-R1.1-01M : Found SPDX license representation - {}'.format(item['detailsUrl']))
                #html_url = '.html'.join(item['detailsUrl'].rsplit('.json', 1))
                html_url = item['detailsUrl'].replace(".json", ".html")
                isOsiApproved = item['isOsiApproved']
                break
        return html_url, isOsiApproved

    def lookup_license_by_name(self, lvalue):
        # TODO - find simpler way to run fuzzy-based search over dict/json (e.g., regex)
        html_url = None
        isOsiApproved = False
        self.logger.info('FsF-R1.1-01M: Search license SPDX details by licence name - {}'.format(lvalue))
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
        related_identifier = 'FsF-I3-01M'  # FsF-I3-01M: Meaningful links to related entities
        related_mname = FAIRCheck.METRICS.get(related_identifier).get('metric_name')
        related_sc = int(FAIRCheck.METRICS.get(related_identifier).get('total_score'))
        related_score = FAIRResultCommonScore(total=related_sc)
        related_result = RelatedResource(id=9, metric_identifier=related_identifier, metric_name=related_mname)
        related_output = RelatedResourceOutputInner()

        # TODO (important) extend mapping to capture relations (linked types, dc,schema.org)
        if self.metadata_merged.get('related_resources'):
            related_output = self.metadata_merged['related_resources']
            related_result.test_status = 'pass'
            related_score.earned = related_sc
        else:
            related_score.earned = 0
            self.logger.warning('FsF-I3-01M : No related resources found in metadata')
        related_result.score = related_score
        related_result.output = related_output
        if self.isDebug:
            related_result.test_debug = self.msg_filter.getMessage(related_identifier)
        return related_result.to_dict()

    def check_searchable(self):
        searchable_identifier = 'FsF-F4-01M'  # FsF-F4-01M: Searchable metadata
        searchable_name = FAIRCheck.METRICS.get(searchable_identifier).get('metric_name')
        searchable_result = Searchable(id=5, metric_identifier=searchable_identifier, metric_name=searchable_name)
        searchable_sc = int(FAIRCheck.METRICS.get(searchable_identifier).get('total_score'))
        searchable_score = FAIRResultCommonScore(total=searchable_sc)
        searchable_output = SearchableOutput()
        search_mechanisms = []
        sources_registry = [MetaDataCollector.Sources.SCHEMAORG_NEGOTIATE.value, MetaDataCollector.Sources.DATACITE_JSON.value]
        all = str([e.value for e in MetaDataCollector.Sources]).strip('[]')
        self.logger.info('FsF-F4-01M : Metadata is retrieved/extracted through - {}'.format(all))
        search_engines_support = [MetaDataCollector.Sources.SCHEMAORG_EMBED.value, MetaDataCollector.Sources.DUBLINCORE.value,
                                  MetaDataCollector.Sources.SIGN_POSTING.value]
        # Check search mechanisms based on sources of metadata extracted.
        search_engine_support_match = list(set(self.metadata_sources).intersection(search_engines_support))
        if search_engine_support_match:
            search_mechanisms.append(OutputSearchMechanisms(mechanism='structured data', mechanism_info=search_engine_support_match))

        registry_support_match = list(set(self.metadata_sources).intersection(sources_registry))
        if registry_support_match:
            search_mechanisms.append(OutputSearchMechanisms(mechanism='metadata registry', mechanism_info=registry_support_match))

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

