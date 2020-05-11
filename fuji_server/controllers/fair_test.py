# -*- coding: utf-8 -*-
"""
preliminary version: https://github.com/huberrob/fuji/blob/master/fuji.py
"""

import json
import logging
import re

import extruct
import idutils
import jmespath
import requests
from extruct.jsonld import JsonLdExtractor

import fuji_server.controllers.mapping as ujimap
from fuji_server.controllers.message_filter import MessageFilter
from fuji_server.controllers.preprocessor import Preprocessor
from fuji_server.models import *
from fuji_server.models import CoreMetadataOutput


class FAIRTest:
    METRICS = None
    SPDX_LICENSES = None
    def __init__(self, uid, oai, test_debug):
        self.oai_pmh = oai
        self.id = uid
        self.pid_url = None  # full pid # e.g., "https://doi.org/10.1594/pangaea.906092 or url (non-pid)
        self.landing_url = None  # url of the landing page of self.pid_url
        self.landing_html = None
        self.pid_scheme = None
        self.metadata = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.isDebug = test_debug
        self.metadata_sources = set()
        self.identifier_sources = set()
        self.license_sources = set()
        if self.isDebug:
            self.msg_filter = MessageFilter()
            self.logger.addFilter(self.msg_filter)
            self.logger.setLevel(logging.INFO)
        FAIRTest.load_predata()

    @classmethod
    def load_predata(cls):
        if not cls.METRICS:
            cls.METRICS = Preprocessor.get_custom_metrics(['metric_name', 'total_score'])
        if not cls.SPDX_LICENSES:
            cls.SPDX_LICENSES = Preprocessor.get_licenses()

    def check_unique_persistent(self):
        uid_metric_identifier = 'FsF-F1-01D'  # FsF-F1-01D: Globally unique identifier
        pid_metric_identifier = 'FsF-F1-02D'  # FsF-F1-02D: Persistent identifier
        uid_metric_name = FAIRTest.METRICS.get(uid_metric_identifier).get('metric_name')
        pid_metric_name = FAIRTest.METRICS.get(pid_metric_identifier).get('metric_name')
        uid_result = Uniqueness(id=1, metric_identifier=uid_metric_identifier, metric_name=uid_metric_name)
        pid_result = Persistence(id=2, metric_identifier=pid_metric_identifier, metric_name=pid_metric_name)
        uid_sc = int(FAIRTest.METRICS.get(uid_metric_identifier).get('total_score'))
        pid_sc = int(FAIRTest.METRICS.get(pid_metric_identifier).get('total_score'))
        uid_score = FAIRResultCommonScore(total=uid_sc)
        pid_score = FAIRResultCommonScore(total=pid_sc)
        uid_output = UniquenessOutput()
        pid_output = PersistenceOutput()

        # ======= TEST 1 - CHECK IDENTIFIER UNIQUENESS =======
        found_ids = idutils.detect_identifier_schemes(self.id)  # some schemes like PMID are generic
        if len(found_ids) > 0:
            self.logger.info('FsF-F1-01D: Unique identifier schemes found {}'.format(found_ids))
            uid_output.guid = self.id
            # identify main scheme
            if len(found_ids) == 1 and found_ids[0] == 'url':  # only url included
                self.pid_url = self.id
            else:
                if 'url' in found_ids:  # ['doi', 'url']
                    found_ids.remove('url')

            found_id = found_ids[0]  # TODO: take the first element of list, e.g., [doi, handle]
            self.logger.info('FsF-F1-01D: Finalized unique identifier scheme - {}'.format(found_id))
            uid_output.guid_scheme = found_id
            uid_result.passed = True
            uid_result.score = uid_score
            uid_result.output = uid_output

            # ======= TEST 2 - CHECK PERSISTENCE =======
            if found_id in ujimap.VALID_PIDS:
                self.pid_scheme = found_id
                # short_pid = id.normalize_pid(self.id, scheme=pid_scheme)
                self.pid_url = idutils.to_url(self.id, scheme=self.pid_scheme)
                self.logger.info('FsF-F1-02D: Persistence identifier scheme - {}'.format(self.pid_scheme))
            else:
                pid_score.earned = 0
                self.logger.warning('FsF-F1-02D: Not a persistent identifier scheme - {}'.format(found_id))

            try:
                self.logger.info('FsF-F1-02D: Retrieving page {}'.format(self.pid_url))
                r = requests.get(self.pid_url)
                code = r.status_code
                self.logger.info('FsF-F1-02D: Request status code - {}'.format(code))
                if code == 200: #TODO 2XX
                    self.landing_url = r.url
                    if re.search('text/html', r.headers['Content-Type'], re.IGNORECASE):
                        self.logger.info('FsF-F1-02D: Found HTML page')
                        self.landing_html = r.text  # this assumes the pid resolves to data landing page (html)
                    else:
                        self.logger.warning('FsF-F1-02D: HTML page NOT FOUND')
                    if self.pid_scheme:
                        pid_score.earned = pid_sc
                        pid_output.pid = self.id
                        pid_output.resolved_url = self.landing_url
                        pid_output.resolvable_status = True
                        pid_output.pid_scheme = self.pid_scheme
                        pid_result.passed = True
            except requests.exceptions.RequestException as e:
                # SSLError or InvalidURL
                self.logger.exception("RequestException: {}".format(e))
                self.logger.exception("FsF-F1-02D: Failed to connect to %s" % self.pid_url)
            pid_result.score = pid_score
            pid_result.output = pid_output
        else:
            self.logger.warning('FsF-F1-01D: Failed to check the identifier scheme!.')

        if self.isDebug:
            uid_result.test_debug = self.msg_filter.getMessage(uid_metric_identifier)
            pid_result.test_debug = self.msg_filter.getMessage(pid_metric_identifier)
        return uid_result.to_dict(), pid_result.to_dict()

    def check_core_metadata(self):
        coremeta_identifier = 'FsF-F2-01M'
        meta_sc = int(FAIRTest.METRICS.get(coremeta_identifier).get('total_score'))
        meta_score = FAIRResultCommonScore(total=meta_sc)
        coremeta_name = FAIRTest.METRICS.get(coremeta_identifier).get('metric_name')
        meta_result = CoreMetadata(id=3, metric_identifier=coremeta_identifier, metric_name=coremeta_name)

        # order should be from least importance to most importance (opegraph -> dc -> schema.org -> datacitejsn)
        source_og, opengraph_dict = self.get_opengraph_metadata()  # extract opengraph metadata
        if opengraph_dict:
            not_null_og = [k for k, v in opengraph_dict.items() if v is not None]
            self.logger.info('FsF-F2-01M: Found Embedded OpenGraph metadata {}'.format(not_null_og))
            if self.isDebug: # TODO - maintain one reference of sources of metadata elements
                if 'object_identifier' in not_null_og:
                    self.identifier_sources.add(source_og)
                if 'license' in not_null_og:
                    self.license_sources.add(source_og)
            self.metadata_sources.add(source_og)
            self.metadata = opengraph_dict
        else:
            self.logger.info('FsF-F2-01M: OpenGraph metadata UNAVAILABLE')

        source_dc, dc_dict = self.get_dc_metadata()  # extract dublin core metadata
        if dc_dict:
            not_null_dc = [k for k, v in dc_dict.items() if v is not None]
            self.logger.info('FsF-F2-01M: Found Embedded DublinCore metadata - {}'.format(not_null_dc))
            if self.isDebug:  # TODO - maintain one reference of sources of metadata elements
                if 'object_identifier' in not_null_dc:
                    self.identifier_sources.add(source_dc)
                if 'license' in not_null_dc:
                    self.license_sources.add(source_dc)
            self.metadata_sources.add(source_dc)
            self.metadata.update(dc_dict) #TODO- update or merge? handle different data types, str vs []
        else:
            self.logger.info('FsF-F2-01M: DublinCore metadata UNAVAILABLE')

        source_schemaorg, schameorg_dict = self.get_schemaorg_metadata()  # extract schema.org json metadata
        if schameorg_dict:
            not_null_sco = [k for k,v in schameorg_dict.items() if v is not None]
            self.logger.info('FsF-F2-01M: Found Schema.org metadata {} '.format(not_null_sco))
            if self.isDebug:  # TODO - maintain one reference of sources of metadata elements
                if 'object_identifier' in not_null_sco:
                    self.identifier_sources.add(source_schemaorg)
                if 'license' in not_null_sco:
                    self.license_sources.add(source_schemaorg)
            self.metadata_sources.add(source_schemaorg)
            self.metadata.update(schameorg_dict)
        else:
            self.logger.info('FsF-F2-01M: Schema.org metadata UNAVAILABLE')

        if self.pid_scheme:
            source_dcitejsn, dcitejsn_dict = self.get_datacite_json()  # extract datacite json if pid available
            if dcitejsn_dict:
                not_null_dcite = [k for k,v in dcitejsn_dict.items() if v is not None]
                self.logger.info('FsF-F2-01M: Found Datacite metadata {} '.format(not_null_dcite))
                if self.isDebug:  # TODO - maintain one reference of sources of metadata elements
                    if 'object_identifier' in not_null_dcite:
                        self.identifier_sources.add(source_dcitejsn)
                    if 'license' in not_null_dcite:
                        self.license_sources.add(source_dcitejsn)
                self.metadata_sources.add(source_dcitejsn)
                self.metadata.update(dcitejsn_dict)
            else:
                self.logger.info('FsF-F2-01M: Datacite metadata UNAVAILABLE')
        else:
            self.logger.info('FsF-F2-01M: Not a PID, no request sent to datacite metadata api.')

        metadata_found = {k: v for k,v in self.metadata.items() if k in ujimap.REQUIRED_CORE_METADATA}
        len_found_metadata = len([k for k,v in metadata_found.items() if v is not None])
        len_metadata_required = len(ujimap.REQUIRED_CORE_METADATA)
        metadata_status = 'no metadata'
        meta_passed = False
        if len_found_metadata == len_metadata_required:
            metadata_status = 'all metadata'
            meta_score.earned = meta_sc
            meta_passed = True
        elif 1 <= len_found_metadata < len_metadata_required:
            metadata_status = 'partial metadata'
            meta_score.earned = meta_sc - 1
            meta_passed = True
        else:
            meta_score.earned = 0

        meta_output: CoreMetadataOutput = CoreMetadataOutput(core_metadata_status=metadata_status, core_metadata_source=list(self.metadata_sources))
        meta_output.core_metadata_found = metadata_found
        meta_result.passed = meta_passed
        meta_result.score = meta_score
        meta_result.output = meta_output
        if self.isDebug:
            meta_result.test_debug = self.msg_filter.getMessage(coremeta_identifier)
        return meta_result.to_dict()

    def get_opengraph_metadata(self):
        # article - Namespace URI: http://ogp.me/ns/article#
        open_metadata = {}
        source = None
        if self.landing_html is not None:
            try:
                self.logger.info('FsF-F2-01M: Extract OpenGraph metadata from html page')
                # get core metadata from opengraph:
                # The Open Graph protocol enables any web page to become a rich object in a social graph
                ext_meta = extruct.extract(self.landing_html.encode('utf8'), syntaxes=['opengraph'])
                if len(ext_meta['opengraph']) > 0:
                    source = ujimap.Sources.OPENGRAPH.value
                    if 'properties' in ext_meta['opengraph'][0]:
                        if len(ext_meta['opengraph'][0]['properties']) > 0:
                            properties = dict(ext_meta['opengraph'][0]['properties'])
                            for p in properties:  # p=og:image
                                if p in ujimap.OG_MAPPING.values():
                                    elem = [key for (key, value) in ujimap.OG_MAPPING.items() if value == p]
                                    elem = elem[0]
                                    open_metadata[elem] = properties[p]
            except:
                self.logger.exception('FsF-F2-01M: Failed to extract OpenGraph metadata')
        return source, open_metadata

    def get_dc_metadata(self):
        dc_core_metadata = {}
        source = None
        if self.landing_html != None:
            try:
                self.logger.info('FsF-F2-01M: Extract DublinCore metadata from html page')
                # get core metadat from dublin core meta tags:
                # < meta name = "DCTERMS.element" content = "Value" / >
                # meta_dc_matches = re.findall('<meta\s+([^\>]*)name=\"(DC|DCTERMS)?\.([a-z]+)\"(.*?)content=\"(.*?)\"',self.landing_html)
                exp = '<\s*meta\s*([^\>]*)name\s*=\s*\"(DC|DCTERMS)?\.([A-Za-z]+)\"(.*?)content\s*=\s*\"(.*?)\"'
                meta_dc_matches = re.findall(exp, self.landing_html)
                if len(meta_dc_matches) > 0:
                    source = ujimap.Sources.DUBLINCORE.value
                    for dc_meta in meta_dc_matches:
                        # dc_meta --> ('', 'DC', 'creator', ' ', 'Hillenbrand, Claus-Dieter')
                        k = dc_meta[2]
                        v = dc_meta[4]
                        # if self.isDebug:
                        # self.logger.info('FsF-F2-01M: DublinCore metadata element, %s = %s , ' % (k, v))
                        if k in ujimap.DC_MAPPING.values():
                            elem = [key for (key, value) in ujimap.DC_MAPPING.items() if value == k][0]
                            if elem in dc_core_metadata:
                                if isinstance(dc_core_metadata[elem], list):
                                    dc_core_metadata[elem].append(v)
                                else:  # string
                                    temp_list = []
                                    temp_list.append(dc_core_metadata[elem])
                                    temp_list.append(v)
                                    dc_core_metadata[elem] = temp_list
                            else:
                                dc_core_metadata[elem] = v
            except Exception as e:
                self.logger.exception('Failed to extract DublinCore - {}'.format(e.traceback.print_exc()))
        return source, dc_core_metadata

    def get_schemaorg_metadata(self):
        source = None
        jsnld_metadata = {}
        if self.landing_html is not None:
            try:
                ext_meta = JsonLdExtractor().extract(self.landing_html.encode('utf8'))
                if ext_meta:
                    source = ujimap.Sources.SCHEMAORG_EMBED.value
                    ext_meta = ext_meta[0]
                else:
                    source = ujimap.Sources.SCHEMAORG_NEGOTIATE.value
                    ext_meta = self.negotiate_datacite('schemaorg_jsonld', 'FsF-F2-01M')

                if ext_meta:
                    self.logger.info('FsF-F2-01M: Extract metadata from {}'.format(source))
                    # TODO filter @type": "Collection" or "@type": "Dataset"
                    # check_context_type = {"@context": "http://schema.org/","@type": "Dataset"}
                    check_context_type = {
                        "@context": ["http://schema.org/",
                                     "http://schema.org"]}  # TODO check syntax - not ending with /
                    if ext_meta['@context'] in check_context_type['@context']:
                        try:
                            jsnld_metadata = jmespath.search(ujimap.SCHEMAORG_MAPPING, ext_meta)
                            if jsnld_metadata['creator'] is None:
                                first = jsnld_metadata['creator_first']
                                last = jsnld_metadata['creator_last']
                                if isinstance(first, list) and isinstance(last, list):
                                    if len(first) == len(last):
                                        names = [i + " " + j for i, j in zip(first, last)]
                                        jsnld_metadata['creator'] = names
                                else:
                                    jsnld_metadata['creator'] = [first + " " + last]
                        except Exception as err:
                            self.logger.debug('Failed to parse JSON-LD schema.org - {}'.format(err))
            except Exception as e:
                self.logger.debug('Failed to extract Schema.org - {}'.format(e.traceback.print_exc()))
        return source, jsnld_metadata

    def get_datacite_json(self):
        source = None
        dcite_metadata = {}
        self.logger.info('FsF-F2-01M: Extract datacite metadata')
        ext_meta = self.negotiate_datacite('datacite_json', 'FsF-F2-01M')
        if ext_meta:
            try:
                dcite_metadata = jmespath.search(ujimap.DATACITE_JSON_MAPPING, ext_meta)
                if dcite_metadata:
                    source = ujimap.Sources.DATACITE_JSON.value

                    if dcite_metadata['creator'] is None:
                        first = dcite_metadata['creator_first']
                        last = dcite_metadata['creator_last']
                        if isinstance(first, list) and isinstance(last, list):
                            if len(first) == len(last):
                                names = [i + " " + j for i, j in zip(first, last)]
                                dcite_metadata['creator'] = names

                    # convert all values (list type) into string except 'creator'
                    for key, value in dcite_metadata.items():
                        if key != 'creator':
                            if isinstance(value, list):
                                flat_keywords = ', '.join(map(str, value))
                                dcite_metadata[key] = flat_keywords
            except Exception as e:
                self.logger.exception('Failed to extract Datacite Json - {}'.format(e.traceback.print_exc()))
        return source, dcite_metadata

    def negotiate_datacite(self, accept_type, metric_id):
        accept = {'datacite_json': 'application/vnd.datacite.datacite+json',
                  'schemaorg_jsonld': 'application/vnd.schemaorg.ld+json',
                  'datacite_xml': 'application/vnd.datacite.datacite+xml'}
        result = None
        if accept_type in accept:
            if self.pid_url is not None:
                try:
                    r = requests.get(self.pid_url, headers={'Accept': accept[accept_type]})
                    self.logger.info(
                        metric_id + ': Content negotiation accept=%s, status=%s ' % (accept_type, str(r.status_code)))
                    if r.status_code == 200:
                        try:
                            result = json.loads(r.text)
                        except ValueError as ve:
                            self.logger.debug(ve)
                            pass #invalid json
                except requests.exceptions.RequestException as e:
                    self.logger.exception("RequestException: {}".format(e))
                    self.logger.exception("FsF-F4-01M: Failed to perform %s content negotiation" % accept_type)
        return result

    def check_data_identifier_included(self):
        did_included_identifier = 'FsF-F3-01M'  # FsF-F3-01M: Inclusion of data identifier in metadata
        included_name = FAIRTest.METRICS.get(did_included_identifier).get('metric_name')
        did_result = IdentifierIncluded(id=4, metric_identifier=did_included_identifier, metric_name=included_name)
        did_sc = int(FAIRTest.METRICS.get(did_included_identifier).get('total_score'))
        did_score = FAIRResultCommonScore(total=did_sc)
        did_output = IdentifierIncludedOutputInner()

        if self.metadata.get('object_content_identifier') is not None: # TODO additional check if provided identifier == identifier in metadata
            did_output.data_identifier_included = self.metadata['object_content_identifier']
            if self.landing_url:
                did_output.data_identifier_active = True
                did_result.passed = True # tests is passed if identifier included in metadata and the identifier is web-accessible
                did_score.earned = did_sc
        else:
            self.logger.warning('FsF-F3-01M: No data identifier is included in metadata - {}'.format(list(self.metadata_sources)))
        did_result.score = did_score
        did_result.output = did_output
        if self.isDebug:
            self.logger.info('FsF-F3-01M: Data identifier metadata sources - {}'.format(list(self.identifier_sources)))
            did_result.test_debug = self.msg_filter.getMessage(did_included_identifier)
        return did_result.to_dict()

    def get_html_typed_links(self): #TODO - item refers to data access url?
        # Use Typed Links in HTTP Link headers to help machines find the resources that make up a publication.
        datalinks = []
        reg_item = '<link rel\s*=\s*\"(item)\"(.*?)href\s*=\s*\"(.*?)\"'
        if self.landing_html != None:
            header_links_matches = re.findall(reg_item, self.landing_html) # ('item', ' ', 'https://doi.pangaea.de/10.1594/PANGAEA.906092?format=zip')
            if len(header_links_matches) > 0:
                for datalink in header_links_matches:
                    datalinks.append(datalink[2])
        return datalinks

    def check_searchable(self):
        searchable_identifier = 'FsF-F4-01M'  # FsF-F4-01M: Searchable metadata
        searchable_result = Searchable(id=5, metric_identifier=searchable_identifier)
        searchable_sc = int(FAIRTest.METRICS.get(searchable_identifier).get('total_score'))
        searchable_score = FAIRResultCommonScore(total=searchable_sc)
        searchable_output = SearchableOutput()
        search_mechanisms = []
        sources_registry = ['Negotiated Schema.org JSON-LD (Datacite)', 'Datacite JsonMetadata']
        # print('self.metadata_sources ', self.metadata_sources)
        r = 'Embedded Schema.org JSON-LD'
        if r in self.metadata_sources:
            search_mechanisms.append(OutputSearchMechanisms(mechanism='structured data', mechanism_info=r))
        if any(x in self.metadata_sources for x in sources_registry):
            search_mechanisms.append(OutputSearchMechanisms(mechanism='metadata registry'))
        # TODO: datacite, oai-pmh
        # print('search_mechanisms ',search_mechanisms)
        length = len(search_mechanisms)
        if length > 0:
            searchable_result.passed = True
            if length == 2:
                searchable_score.earned = searchable_sc  # TODO: incremental scoring
            if length == 1:
                searchable_score.earned = searchable_sc - 1
            searchable_result.score = searchable_score
            searchable_output.search_mechanisms = search_mechanisms
            searchable_result.output = searchable_output
        else:
            self.logger.warning('No search mechanism supported')
        return searchable_result.to_dict()

    def check_license(self):
        license_identifier = 'FsF-R1.1-01M'  # FsF-R1.1-01M: Data Usage Licence
        license_mname = FAIRTest.METRICS.get(license_identifier).get('metric_name')
        license_sc = int(FAIRTest.METRICS.get(license_identifier).get('total_score'))
        license_score = FAIRResultCommonScore(total=license_sc)
        license_result = License(id=6, metric_identifier=license_identifier, metric_name=license_mname)
        license_output = LicenseOutputInner()

        #https://spdx.org/licenses/0BSD.html#licenseText
        if self.metadata.get('license') is not None:
            license_output.license = self.metadata['license']
            # license maybe name or uri
            isurl = idutils.is_url(self.metadata['license'])
            if not isurl: # maybe licence name
                spdx_html, spdx_osi = self.lookup_license(self.metadata['license'])
                license_output.details_url = spdx_html
                license_output.osi_approved = spdx_osi
            else: # TODO - use url to match spdx information
                self.logger.info('FsF-R1.1-01M: License url provided, cannot determined spdx "details_url" and "osi_approved"')
                license_output.details_url = None # TODO - seeAlso from spdx may contain license url specified
                license_output.osi_approved = None
            license_result.passed = True
            license_score.earned = license_sc
        else:
            license_score.earned = 0
            self.logger.warning('FsF-R1.1-01M: No license information is included in metadata - {}'.format(list(self.metadata_sources)))
        license_result.score = license_score
        license_result.output = license_output

        if self.isDebug:
            self.logger.info(
                    'FsF-R1.1-01M: License metadata sources - {}'.format(list(self.license_sources)))
            license_result.test_debug = self.msg_filter.getMessage(license_identifier)
        return license_result.to_dict()

    def lookup_license(self, lname):
        html_url = None
        isOsiApproved = False
        # TODO - better string matching
        #  (Creative Commons Attribution 4.0 International vs Creative Commons Attribution 4.0 International (CC BY 4.0))
        found = next((item for item in FAIRTest.SPDX_LICENSES if item['name'] == lname.lower()), None)
        self.logger.info('FsF-R1.1-01M: Extract license SPDX details by name - {}'.format(lname))
        if found:
            self.logger.info('FsF-R1.1-01M: Found SPDX license representation - {}'.format(found['detailsUrl']))
            html_url = '.html'.join(found['detailsUrl'].rsplit('.json', 1))
            isOsiApproved = found['isOsiApproved']
        else:
            self.logger.info('FsF-R1.1-01M: No SPDX license representation found')
        return html_url , isOsiApproved
