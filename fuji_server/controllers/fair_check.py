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

import logging
import mimetypes
import re
import sys
import urllib
import urllib.request as urllib
from typing import List, Any
from urllib.parse import urlparse

import Levenshtein
import idutils
import lxml
import rdflib
from rdflib.namespace import RDF
from rdflib.namespace import DCTERMS
from rdflib.namespace import DC
from rapidfuzz import fuzz
from rapidfuzz import process
from tika import parser

from fuji_server.evaluators.fair_evaluator_persistent_identifier import FAIREvaluatorPersistentIdentifier
from fuji_server.evaluators.fair_evaluator_unique_identifier import FAIREvaluatorUniqueIdentifier
from fuji_server.evaluators.fair_evaluator_minimal_metadata import FAIREvaluatorCoreMetadata

from fuji_server.helper.log_message_filter import MessageFilter
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.metadata_collector_datacite import MetaDataCollectorDatacite
from fuji_server.helper.metadata_collector_dublincore import MetaDataCollectorDublinCore
from fuji_server.helper.metadata_collector_microdata import MetaDataCollectorMicroData
from fuji_server.helper.metadata_collector_rdf import MetaDataCollectorRdf
from fuji_server.helper.metadata_collector_schemaorg import MetaDataCollectorSchemaOrg
from fuji_server.helper.metadata_collector_xml import MetaDataCollectorXML
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.metadata_provider_oai import OAIMetadataProvider
from fuji_server.helper.metadata_provider_sparql import SPARQLMetadataProvider
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.repository_helper import RepositoryHelper
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from fuji_server.models import *
from fuji_server.models import CoreMetadataOutput, CommunityEndorsedStandardOutputInner
from fuji_server.models.data_content_metadata import DataContentMetadata
from fuji_server.models.data_content_metadata_output import DataContentMetadataOutput
from fuji_server.models.data_provenance import DataProvenance
from fuji_server.models.data_provenance_output import DataProvenanceOutput
from fuji_server.models.metadata_preserved import MetadataPreserved
from fuji_server.models.metadata_preserved_output import MetadataPreservedOutput
from fuji_server.models.standardised_protocol import StandardisedProtocol
from fuji_server.models.standardised_protocol_output import StandardisedProtocolOutput


class FAIRCheck:
    METRICS = None
    SPDX_LICENSES = None
    SPDX_LICENSE_NAMES = None
    COMMUNITY_STANDARDS_NAMES = None
    COMMUNITY_METADATA_STANDARDS_URIS = None
    COMMUNITY_METADATA_STANDARDS_URIS_LIST = None
    COMMUNITY_STANDARDS = None
    SCIENCE_FILE_FORMATS = None
    LONG_TERM_FILE_FORMATS = None
    OPEN_FILE_FORMATS = None
    DEFAULT_NAMESPACES = None
    VOCAB_NAMESPACES = None
    ARCHIVE_MIMETYPES = Mapper.ARCHIVE_COMPRESS_MIMETYPES.value
    STANDARD_PROTOCOLS = None
    FILES_LIMIT = None

    def __init__(self, uid, test_debug=False, oaipmh=None):
        self.id = uid
        self.oaipmh_endpoint = oaipmh
        self.pid_url = None  # full pid # e.g., "https://doi.org/10.1594/pangaea.906092 or url (non-pid)
        self.landing_url = None  # url of the landing page of self.pid_url
        self.landing_html = None
        self.landing_origin = None  # schema + authority of the landing page e.g. https://www.pangaea.de
        self.pid_scheme = None
        self.id_scheme= None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metadata_sources = []
        self.isDebug = test_debug
        self.isMetadataAccessible = None
        self.metadata_merged = {}
        self.content_identifier=[]
        self.community_standards = []
        self.community_standards_uri = {}
        self.namespace_uri=[]
        self.reference_elements = Mapper.REFERENCE_METADATA_LIST.value.copy()  # all metadata elements required for FUJI metrics
        self.related_resources = []
       # self.test_data_content_text = None# a helper to check metadata against content
        self.rdf_graph = None
        self.sparql_endpoint = None
        self.rdf_collector = None
        if self.isDebug:
            self.msg_filter = MessageFilter()
            self.logger.addFilter(self.msg_filter)
            self.logger.setLevel(logging.INFO)  # set to debug in testing environment
        self.count = 0
        FAIRCheck.load_predata()
        self.extruct = None
        self.tika_content_types_list = []


    @classmethod
    def load_predata(cls):
        cls.FILES_LIMIT = Preprocessor.data_files_limit
        if not cls.METRICS:
            cls.METRICS = Preprocessor.get_custom_metrics(['metric_name', 'total_score'])
        if not cls.SPDX_LICENSES:
            # cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES, cls.SPDX_LICENSE_URLS = Preprocessor.get_licenses()
            cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES = Preprocessor.get_licenses()
        if not cls.COMMUNITY_METADATA_STANDARDS_URIS:
            cls.COMMUNITY_METADATA_STANDARDS_URIS = Preprocessor.get_metadata_standards_uris()
            cls.COMMUNITY_METADATA_STANDARDS_URIS_LIST = list(cls.COMMUNITY_METADATA_STANDARDS_URIS.keys())
        if not cls.COMMUNITY_STANDARDS:
            cls.COMMUNITY_STANDARDS = Preprocessor.get_metadata_standards()
            cls.COMMUNITY_STANDARDS_NAMES = list(cls.COMMUNITY_STANDARDS.keys())
        if not cls.SCIENCE_FILE_FORMATS:
            cls.SCIENCE_FILE_FORMATS = Preprocessor.get_science_file_formats()
        if not cls.LONG_TERM_FILE_FORMATS:
            cls.LONG_TERM_FILE_FORMATS = Preprocessor.get_long_term_file_formats()
        if not cls.OPEN_FILE_FORMATS:
            cls.OPEN_FILE_FORMATS = Preprocessor.get_open_file_formats()
        if not cls.DEFAULT_NAMESPACES:
            cls.DEFAULT_NAMESPACES = Preprocessor.getDefaultNamespaces()
        if not cls.VOCAB_NAMESPACES:
            cls.VOCAB_NAMESPACES = Preprocessor.getLinkedVocabs()
        if not cls.STANDARD_PROTOCOLS:
            cls.STANDARD_PROTOCOLS = Preprocessor.get_standard_protocols()

    @staticmethod
    def uri_validator(u):  # TODO integrate into request_helper.py
        try:
            r = urlparse(u)
            return all([r.scheme, r.netloc])
        except:
            return False

    def check_unique_identifier(self):
        unique_identifier_check = FAIREvaluatorUniqueIdentifier(self)
        unique_identifier_check.set_metric('FsF-F1-01D', metrics=FAIRCheck.METRICS)
        return unique_identifier_check.getResult()

    def check_persistent_identifier(self):
        persistent_identifier_check = FAIREvaluatorPersistentIdentifier(self)
        persistent_identifier_check.set_metric('FsF-F1-02D', metrics=FAIRCheck.METRICS)
        return persistent_identifier_check.getResult()

    def check_unique_persistent(self):
        return self.check_unique_identifier(), self.check_persistent_identifier()
        '''
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
        schemes = [i[0] for i in idutils.PID_SCHEMES]
        self.logger.info('FsF-F1-01D : Using idutils schemes')
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
            self.logger.info('FsF-F1-02D : PID schemes-based assessment supported by the assessment service - {}'.format(Mapper.VALID_PIDS.value))
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
            neg_source, result = requestHelper.content_negotiate('FsF-F1-02D')
            #TODO: what if other protocols are used e.g. FTP etc..
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
                    self.logger.info('FsF-F1-02D : Object identifier active (status code = 200)')
                    self.isMetadataAccessible = True
                else:
                    if r.status_code in [401, 402, 403]:
                        self.isMetadataAccessible = False
                    #if r.status_code == 401:
                        #response = requests.get(self.pid_url, auth=HTTPBasicAuth('user', 'pass'))
                    self.logger.warning("Resource inaccessible, identifier returned http status code: {code}".format(code=r.status_code))
            pid_result.score = pid_score
            pid_result.output = pid_output

            if self.isDebug:
                uid_result.test_debug = self.msg_filter.getMessage(uid_metric_identifier)
                pid_result.test_debug = self.msg_filter.getMessage(pid_metric_identifier)
        else:
            self.logger.warning('FsF-F1-01D : Failed to check the identifier scheme!.')

        self.retrieve_metadata(result)
        return uid_result.to_dict(), pid_result.to_dict()
        '''

    def retrieve_metadata(self, extruct_metadata):
        if isinstance(extruct_metadata, dict):
            embedded_exists = {k: v for k, v in extruct_metadata.items() if v}
            self.extruct = embedded_exists.copy()
            if embedded_exists:  # retrieve metadata from landing page
                self.logger.info(
                    'FsF-F2-01M : Formats of structured metadata embedded in HTML markup - {}'.format(
                        list(embedded_exists.keys())))
                self.retrieve_metadata_embedded(embedded_exists)
            else:
                self.logger.warning('FsF-F2-01M : NO structured metadata embedded in HTML')

        if self.reference_elements:  # this will be always true as we need datacite client id
            self.retrieve_metadata_external()

        # ========= clean merged metadata, delete all entries which are None or ''
        data_objects = self.metadata_merged.get('object_content_identifier')
        if data_objects == {'url': None} or data_objects == [None]:
            data_objects = self.metadata_merged['object_content_identifier'] = None
        if data_objects is not None:
            if not isinstance(data_objects, list):
                self.metadata_merged['object_content_identifier']=[data_objects]

        # TODO quick-fix to merge size information - should do it at mapper
        if 'object_content_identifier' in self.metadata_merged:
            if self.metadata_merged.get('object_content_identifier'):
                for c in self.metadata_merged['object_content_identifier']:
                    if not c.get('size') and self.metadata_merged.get('object_size'):
                        c['size'] = self.metadata_merged.get('object_size')

        for mk, mv in list(self.metadata_merged.items()):
            if mv == '' or mv is None:
                del self.metadata_merged[mk]

        self.logger.info('FsF-F2-01M : Type of object described by the metadata - {}'.format(self.metadata_merged.get('object_type')))

        # detect api and standards
        self.retrieve_apis_standards()

        # remove duplicates
        if self.namespace_uri:
            self.namespace_uri = list(set(self.namespace_uri))

    def retrieve_apis_standards(self):
        self.logger.info('FsF-R1.3-01M : Retrieving API and Standards')
        client_id = self.metadata_merged.get('datacite_client')
        self.logger.info('FsF-R1.3-01M : re3data/datacite client id - {}'.format(client_id))

        if self.oaipmh_endpoint:
            self.logger.info('{} : OAI-PMH endpoint provided as part of the request.'.format('FsF-R1.3-01M'))
        else:
            #find endpoint via datacite/re3data if pid is provided
            if client_id and self.pid_scheme:
                self.logger.info('{} : Inferring endpoint information through re3data/datacite services'.format('FsF-R1.3-01M'))
                repoHelper = RepositoryHelper(client_id, self.pid_scheme)
                repoHelper.lookup_re3data()
                self.oaipmh_endpoint = repoHelper.getRe3MetadataAPIs().get('OAI-PMH')
                self.sparql_endpoint = repoHelper.getRe3MetadataAPIs().get('SPARQL')
                self.community_standards.extend(repoHelper.getRe3MetadataStandards())
                self.logger.info('{} : Metadata standards listed in re3data record - {}'.format('FsF-R1.3-01M', self.community_standards ))

        # retrieve metadata standards info from oai-pmh
        if self.oaipmh_endpoint:
            self.logger.info('{} : Use OAI-PMH endpoint to retrieve standards used by the repository - {}'.format('FsF-R1.3-01M',self.oaipmh_endpoint))
            if (self.uri_validator(self.oaipmh_endpoint)):
                oai_provider = OAIMetadataProvider(endpoint=self.oaipmh_endpoint, logger=self.logger,metric_id='FsF-R1.3-01M')
                self.community_standards_uri = oai_provider.getMetadataStandards()
                self.namespace_uri.extend(oai_provider.getNamespaces())
                stds = None
                if self.community_standards_uri:
                    stds = list(self.community_standards_uri.keys())
                self.logger.info('{} : Selected standards that are listed in OAI-PMH endpoint - {}'.format('FsF-R1.3-01M',stds ))
            else:
                self.logger.info('{} : Invalid endpoint'.format('FsF-R1.3-01M'))
        else:
            self.logger.warning('{} : NO OAI-PMH endpoint found'.format('FsF-R1.3-01M'))


    def retrieve_metadata_embedded(self, extruct_metadata):
        isPid = False
        if self.pid_scheme:
            isPid = True
        # ========= retrieve embedded rdfa and microdata metadata ========
        micro_meta = extruct_metadata.get('microdata')
        microdata_collector = MetaDataCollectorMicroData(loggerinst=self.logger, sourcemetadata=micro_meta,
                                                   mapping=Mapper.MICRODATA_MAPPING)
        source_micro, micro_dict = microdata_collector.parse_metadata()
        if micro_dict:
            self.metadata_sources.append(source_micro)
            self.namespace_uri.extend(microdata_collector.getNamespaces())
            micro_dict = self.exclude_null(micro_dict)
            for i in micro_dict.keys():
                if i in self.reference_elements:
                    self.metadata_merged[i] = micro_dict[i]
                    self.reference_elements.remove(i)
        # RDFa
        RDFA_ns = rdflib.Namespace("http://www.w3.org/ns/rdfa#")
        rdfasource = MetaDataCollector.Sources.RDFA.value
        rdfagraph = None
        errors=[]
        try:
            rdfagraph = rdflib.Graph()
            rdfagraph.parse(data=self.landing_html, format='rdfa')
            rdfa_collector = MetaDataCollectorRdf(loggerinst=self.logger, target_url=self.landing_url, source=rdfasource,
                                                  rdf_graph=rdfagraph)
            source_rdfa, rdfa_dict = rdfa_collector.parse_metadata()
            self.metadata_sources.append(rdfasource)
            self.namespace_uri.extend(rdfa_collector.getNamespaces())
            #rdfa_dict['object_identifier']=self.pid_url
            rdfa_dict = self.exclude_null(rdfa_dict)
            for i in rdfa_dict.keys():
                if i in self.reference_elements:
                    self.metadata_merged[i] = rdfa_dict[i]
                    self.reference_elements.remove(i)
        except:
            self.logger.warning('FsF-F2-01M : RDFa metadata parsing exception')

        # ========= retrieve schema.org (embedded, or from via content-negotiation if pid provided) =========
        ext_meta = extruct_metadata.get('json-ld')
        schemaorg_collector = MetaDataCollectorSchemaOrg(loggerinst=self.logger, sourcemetadata=ext_meta,
                                                         mapping=Mapper.SCHEMAORG_MAPPING,
                                                         ispid=isPid, pidurl=self.pid_url)
        source_schemaorg, schemaorg_dict = schemaorg_collector.parse_metadata()
        schemaorg_dict = self.exclude_null(schemaorg_dict)
        if schemaorg_dict:
            self.namespace_uri.extend(schemaorg_collector.namespaces)
            #not_null_sco = [k for k, v in schemaorg_dict.items() if v is not None]
            self.metadata_sources.append(source_schemaorg)
            if schemaorg_dict.get('related_resources'):
                self.related_resources.extend(schemaorg_dict.get('related_resources'))
            # add object type for future reference
            for i in schemaorg_dict.keys():
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
            dc_dict = self.exclude_null(dc_dict)
            if dc_dict:
                self.namespace_uri.extend(dc_collector.namespaces)
                #not_null_dc = [k for k, v in dc_dict.items() if v is not None]
                self.metadata_sources.append(source_dc)
                if dc_dict.get('related_resources'):
                    self.related_resources.extend(dc_dict.get('related_resources'))
                for d in dc_dict.keys():
                    if d in self.reference_elements:
                        self.metadata_merged[d] = dc_dict[d]
                        self.reference_elements.remove(d)
            else:
                self.logger.info('FsF-F2-01M : DublinCore metadata UNAVAILABLE')

        #========= retrieve typed links =========
        if self.metadata_merged.get('object_content_identifier') is None:
            links = self.get_html_typed_links(rel='item')
            if links:
                self.metadata_merged['object_content_identifier'] = links
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

    def get_guessed_xml_link(self):
        # in case object landing page URL ends with '.html' or '/html'
        # try to find out if there is some xml content if suffix is replaced by 'xml
        datalink = None
        if self.landing_url is not None:
            suff_res = re.search(r".*[\.\/](html?)?$", self.landing_url)
            if suff_res is not None:
                if suff_res[1] is not None:
                    guessed_link = self.landing_url.replace(suff_res[1],'xml')
                    try:
                        response=urllib.urlopen(guessed_link)
                        if response.getheader('Content-Type') in ['text/xml','application/rdf+xml']:
                            datalink={'source':'guessed','url': guessed_link, 'type': response.getheader('Content-Type'), 'rel': 'alternate'}
                            self.logger.info('FsF-F2-01M : Found XML content at: '+guessed_link)

                    except:
                        self.logger.info('FsF-F2-01M : Guessed XML retrieval failed for: '+guessed_link)
        return datalink

    def retrieve_metadata_external(self):
        # ========= retrieve xml metadata namespaces by content negotiation ========
        if self.landing_url is not None:
            negotiated_xml_collector = MetaDataCollectorXML(loggerinst=self.logger,target_url=self.landing_url, link_type='negotiated')
            source_neg_xml, metadata_neg_xml = negotiated_xml_collector.parse_metadata()

        # ========= retrieve datacite json metadata based on pid =========
        if self.pid_scheme:
            dcite_collector = MetaDataCollectorDatacite(mapping=Mapper.DATACITE_JSON_MAPPING, loggerinst=self.logger,
                                                        pid_url=self.pid_url)
            source_dcitejsn, dcitejsn_dict = dcite_collector.parse_metadata()
            dcitejsn_dict = self.exclude_null(dcitejsn_dict)
            if dcitejsn_dict:
                # not_null_dcite = [k for k, v in dcitejsn_dict.items() if v is not None]
                self.metadata_sources.append(source_dcitejsn)
                if dcitejsn_dict.get('related_resources'):
                    self.related_resources.extend(dcitejsn_dict.get('related_resources'))

                for r in dcitejsn_dict.keys():
                    # only merge when the value cannot be retrived from embedded metadata
                    if r in self.reference_elements and not self.metadata_merged.get(r):
                        self.metadata_merged[r] = dcitejsn_dict[r]
                        self.reference_elements.remove(r)
            else:
                self.logger.info('FsF-F2-01M : Datacite metadata UNAVAILABLE')
        else:
            self.logger.info('FsF-F2-01M : Not a PID, therefore Datacite metadata (json) not requested.')

        found_metadata_link =False
        typed_metadata_links = self.get_html_typed_links(rel='alternate')
        guessed_metadata_link = self.get_guessed_xml_link()
        if guessed_metadata_link is not None:
            typed_metadata_links.append(guessed_metadata_link)

        for metadata_link in typed_metadata_links:
            if metadata_link['type'] in ['application/rdf+xml','text/n3','text/ttl','application/ld+json']:
                self.logger.info('FsF-F2-01M : Found Typed Links in HTML Header linking to RDF Metadata ('+str(metadata_link['type']+')'))
                found_metadata_link=True
                source = MetaDataCollector.Sources.RDF_SIGN_POSTING.value
                self.rdf_collector = MetaDataCollectorRdf(loggerinst=self.logger, target_url=metadata_link['url'], source=source )
                break
            elif metadata_link['type'] == 'text/xml':
                xml_collector = MetaDataCollectorXML(loggerinst=self.logger,
                                                           target_url=metadata_link['url'], link_type=metadata_link['source'])
                xml_collector.parse_metadata()
                xml_namespaces = xml_collector.getNamespaces()

        if not found_metadata_link:
            #TODO: find a condition to trigger the rdf request
            source = MetaDataCollector.Sources.LINKED_DATA.value
            if self.landing_url is not None:
                self.rdf_collector = MetaDataCollectorRdf(loggerinst=self.logger, target_url=self.landing_url, source=source)

        if self.rdf_collector is not None:
            source_rdf, rdf_dict = self.rdf_collector.parse_metadata()
            self.namespace_uri.extend(self.rdf_collector.getNamespaces())
            rdf_dict = self.exclude_null(rdf_dict)
            if rdf_dict:
                # not_null_rdf = [k for k, v in rdf_dict.items() if v is not None]
                # self.logger.info('FsF-F2-01M : Found Datacite metadata {} '.format(not_null_dcite))
                self.metadata_sources.append(source_rdf)
                for r in rdf_dict.keys():
                    if r in self.reference_elements:
                        self.metadata_merged[r] = rdf_dict[r]
                        self.reference_elements.remove(r)
            else:
                self.logger.info('FsF-F2-01M : Linked Data metadata UNAVAILABLE')

        if self.reference_elements:
            self.logger.debug('Reference metadata elements NOT FOUND - {}'.format(self.reference_elements))
        else:
            self.logger.debug('FsF-F2-01M : ALL reference metadata elements available')

    def exclude_null(self, dt):
        if type(dt) is dict:
            return dict((k, self.exclude_null(v)) for k, v in dt.items() if v and self.exclude_null(v))
        elif type(dt) is list:
            return [self.exclude_null(v) for v in dt if v and self.exclude_null(v)]
        else:
            return dt



    def check_minimal_metatadata(self):

        core_metadata_check = FAIREvaluatorCoreMetadata(self)
        core_metadata_check.set_metric('FsF-F2-01M', metrics=FAIRCheck.METRICS)
        return core_metadata_check.getResult()
    '''
        self.count += 1
        coremeta_identifier = 'FsF-F2-01M'
        meta_sc = int(FAIRCheck.METRICS.get(coremeta_identifier).get('total_score'))
        meta_score = FAIRResultCommonScore(total=meta_sc)
        coremeta_name = FAIRCheck.METRICS.get(coremeta_identifier).get('metric_name')
        meta_result = CoreMetadata(id=self.count, metric_identifier=coremeta_identifier, metric_name=coremeta_name)
        metadata_required = Mapper.REQUIRED_CORE_METADATA.value
        metadata_found = {k: v for k, v in self.metadata_merged.items() if k in metadata_required}
        self.logger.info('FsF-F2-01M : Required core metadata elements {}'.format(metadata_required))

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
            self.logger.info('FsF-F2-01M : Not all required metadata elements exists, so set the status as = insufficient metadata')
            metadata_status = 'insufficient metadata' # status should follow enumeration in yaml

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
        '''

    def check_content_identifier_included(self):
        self.count += 1
        did_included_identifier = 'FsF-F3-01M'  # FsF-F3-01M: Inclusion of data identifier in metadata
        included_name = FAIRCheck.METRICS.get(did_included_identifier).get('metric_name')
        did_result = IdentifierIncluded(id=self.count, metric_identifier=did_included_identifier, metric_name=included_name)
        did_sc = int(FAIRCheck.METRICS.get(did_included_identifier).get('total_score'))
        did_score = FAIRResultCommonScore(total=did_sc)
        did_output = IdentifierIncludedOutput()

        #id_object = None
        id_object = self.metadata_merged.get('object_identifier')
        did_output.object_identifier_included = id_object
        contents = self.metadata_merged.get('object_content_identifier')

        if id_object is not None:
            self.logger.info('FsF-F3-01M : Object identifier specified {}'.format(id_object))
        score = 0
        # This (check if object id is active) is already done ein check_unique_persistent
        '''
        if FAIRCheck.uri_validator(
                id_object):  # TODO: check if specified identifier same is provided identifier (handle pid and non-pid cases)
            # check resolving status
            try:
                request = requests.get(id_object)
                if request.status_code == 200:

                    self.logger.info('FsF-F3-01M : Object identifier active (status code = 200)')
                    score += 1
                else:
                    if request.status_code in [401,402,403]:
                        self.isRestricted = True
                    self.logger.warning("Identifier returned response code: {code}".format(code=request.status_code))
            except:
                self.logger.warning('FsF-F3-01M : Object identifier does not exist or could not be accessed {}'.format(id_object))
        else:
            self.logger.warning('FsF-F3-01M : Invalid Identifier - {}'.format(id_object))
        '''
        content_list = []
        if contents:
            if isinstance(contents, dict):
                contents = [contents]
            contents = [c for c in contents if c]
            number_of_contents = len(contents)
            self.logger.info('FsF-F3-01M : Number of object content identifier found - {}'.format(number_of_contents))

            if number_of_contents >= FAIRCheck.FILES_LIMIT:
                self.logger.info('FsF-F3-01M : The total number of object (content) specified is above threshold, so use the first {} content identifiers'.format(FAIRCheck.FILES_LIMIT))
                contents = contents[:FAIRCheck.FILES_LIMIT]

            for content_link in contents:
                if content_link.get('url'):
                    #self.logger.info('FsF-F3-01M : Object content identifier included {}'.format(content_link.get('url')))
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
                            'FsF-F3-01M : Content identifier {0} inaccessible, HTTPError code {1} '.format(content_link.get('url'), e.code))
                    except urllib.URLError as e:
                        self.logger.exception(e.reason)
                    except:
                        self.logger.warning('FsF-F3-01M : Could not access the resource')
                    else:  # will be executed if there is no exception
                        self.content_identifier.append(content_link)
                        did_output_content.content_identifier_active = True
                        content_list.append(did_output_content)
                else:
                    self.logger.warning('FsF-F3-01M : Object (content) url is empty - {}'.format(content_link))

        else:
            self.logger.warning('FsF-F3-01M : Data (content) identifier is missing.')

        if content_list:
            score += 1
        did_score.earned = score
        if score > 0:
            did_result.test_status = "pass"

        did_output.content = content_list
        did_result.output = did_output
        did_result.score = did_score

        if self.isDebug:
            did_result.test_debug = self.msg_filter.getMessage(did_included_identifier)
        return did_result.to_dict()

    def check_data_access_level(self):
        #Focus on machine readable rights -> URIs only
        #1) http://vocabularies.coar-repositories.org/documentation/access_rights/
        #2) Eprints AccessRights Vocabulary: check for http://purl.org/eprint/accessRights/
        #3) EU publications access rights check for http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC
        #4) Openaire Guidelines <dc:rights>info:eu-repo/semantics/openAccess</dc:rights>
        self.count += 1
        access_identifier = 'FsF-A1-01M'
        access_name = FAIRCheck.METRICS.get(access_identifier).get('metric_name')
        access_sc = int(FAIRCheck.METRICS.get(access_identifier).get('total_score'))
        access_score = FAIRResultCommonScore(total=access_sc)
        access_result = DataAccessLevel(self.count, metric_identifier=access_identifier, metric_name=access_name)
        access_output = DataAccessOutput()
        #rights_regex = r'((\/licenses|purl.org\/coar\/access_right|purl\.org\/eprint\/accessRights|europa\.eu\/resource\/authority\/access-right)\/{1}(\S*))'
        rights_regex = r'((\/creativecommons\.org|info\:eu\-repo\/semantics|purl.org\/coar\/access_right|purl\.org\/eprint\/accessRights|europa\.eu\/resource\/authority\/access-right)\/{1}(\S*))'

        access_level = None
        access_details = {}
        score = 0
        test_status = "fail"
        exclude = []
        access_rights = self.metadata_merged.get('access_level')

        #access_rights can be None or []
        if access_rights:
            self.logger.info('FsF-A1-01M : Found access rights information in dedicated metadata element')
            access_rights = 'info:eu-repo/semantics/restrictedAccess'
            if isinstance(access_rights, str):
                access_rights = [access_rights]
            for access_right in access_rights:
                self.logger.info('FsF-A1-01M : Access information specified - {}'.format(access_right))
                if not self.isLicense(access_right, access_identifier):  # exclude license-based text from access_rights
                    rights_match = re.search(rights_regex, access_right, re.IGNORECASE)
                    if rights_match is not None:
                        last_group = len(rights_match.groups())
                        filtered_rights = rights_match[last_group]
                        for right_code, right_status in Mapper.ACCESS_RIGHT_CODES.value.items():
                            if re.search(right_code, filtered_rights, re.IGNORECASE):
                                access_level = right_status
                                access_details['access_condition'] = rights_match[1] #overwrite existing condition
                                self.logger.info('FsF-A1-01M : Access level recognized as ' + str(right_status))
                                break
                        break
                    else:
                        self.logger.info('FsF-A1-01M : Not a standardized access level')
                else:
                    self.logger.warning('FsF-A1-01M : Access condition looks like license, therefore the following is ignored - {}'.format(access_right))
                    exclude.append(access_right)
            if not access_details and access_rights:
                access_rights = set(access_rights) - set(exclude)
                if access_rights :
                    access_details['access_condition'] = ', '.join(access_rights)
        else:
            self.logger.warning('FsF-A1-01M : NO access information is available in metadata')
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

    def check_license(self):
        self.count += 1
        license_identifier = 'FsF-R1.1-01M'  # FsF-R1.1-01M: Data Usage Licence
        license_mname = FAIRCheck.METRICS.get(license_identifier).get('metric_name')
        license_sc = int(FAIRCheck.METRICS.get(license_identifier).get('total_score'))
        license_score = FAIRResultCommonScore(total=license_sc)
        license_result = License(id=self.count, metric_identifier=license_identifier, metric_name=license_mname)
        licenses_list = []
        specified_licenses = self.metadata_merged.get('license')

        if specified_licenses is not None and specified_licenses !=[]:
            if isinstance(specified_licenses, str):  # licenses maybe string or list depending on metadata schemas
                specified_licenses = [specified_licenses]
            for l in specified_licenses:
                license_output = LicenseOutputInner()
                #license can be dict or
                license_output.license = l
                if isinstance(l, str):
                    isurl = idutils.is_url(l)
                if isurl:
                    spdx_html, spdx_osi = self.lookup_license_by_url(l, license_identifier)
                else:  # maybe licence name
                    spdx_html, spdx_osi = self.lookup_license_by_name(l, license_identifier)
                if not spdx_html:
                    self.logger.warning('FsF-R1.1-01M : NO SPDX license representation (spdx url, osi_approved) found')
                license_output.details_url = spdx_html
                license_output.osi_approved = spdx_osi
                licenses_list.append(license_output)
            license_result.test_status = "pass"
            license_score.earned = license_sc
        else:
            license_score.earned = 0
            self.logger.warning('FsF-R1.1-01M : License unavailable')

        license_result.output = licenses_list
        license_result.score = license_score

        if self.isDebug:
            license_result.test_debug = self.msg_filter.getMessage(license_identifier)
        return license_result.to_dict()

    def lookup_license_by_url(self, u, metric_id):
        self.logger.info('{0} : Verify URL through SPDX registry - {1}'.format(metric_id, u))
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
        self.logger.info('{0} : Verify name through SPDX registry - {1}'.format(metric_id, lvalue))
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
        related_output = RelatedResourceOutput()
        self.logger.info('{0} : Total number of related resources extracted - {1}'.format(related_identifier, len(self.related_resources)))

        #if self.metadata_merged.get('related_resources'):
        if self.related_resources:
            #QC check: exclude potential incorrect relation
            self.related_resources = [item for item in self.related_resources if item.get('related_resource') != self.pid_url]
            self.logger.info('{0} : Number of related resources after QC step - {1}'.format(related_identifier, len(self.related_resources)))

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
        sources_registry = [MetaDataCollector.Sources.DATACITE_JSON.value]
        all = str([e.value for e in MetaDataCollector.Sources]).strip('[]')
        self.logger.info('FsF-F4-01M : Supported tests of metadata retrieval/extraction - {}'.format(all))
        search_engines_support = [MetaDataCollector.Sources.SCHEMAORG_NEGOTIATE.value,
                                  MetaDataCollector.Sources.SCHEMAORG_EMBED.value,
                                  MetaDataCollector.Sources.DUBLINCORE.value,
                                  MetaDataCollector.Sources.SIGN_POSTING.value,
                                  MetaDataCollector.Sources.RDFA.value,
                                  MetaDataCollector.Sources.LINKED_DATA.value,
                                  MetaDataCollector.Sources.LINKED_DATA.RDF_SIGN_POSTING.value]

        # Check search mechanisms based on sources of metadata extracted.
        search_engine_support_match: List[Any] = list(set(self.metadata_sources).intersection(search_engines_support))
        if search_engine_support_match:
            search_mechanisms.append(
                OutputSearchMechanisms(mechanism='structured data', mechanism_info=search_engine_support_match))
            self.logger.info('FsF-F4-01M : Metadata found through - structured data')
        else:
            self.logger.warning('FsF-F4-01M : Metadata is NOT found through - {}'.format(search_engines_support))

        registry_support_match = list(set(self.metadata_sources).intersection(sources_registry))
        if registry_support_match:
            search_mechanisms.append(
                OutputSearchMechanisms(mechanism='metadata registry', mechanism_info=registry_support_match))
            self.logger.info('FsF-F4-01M : Metadata found through - metadata registry')
        else:
            self.logger.warning('FsF-F4-01M : Metadata is NOT found through registries considered by the assessment service  - {}'.format(sources_registry))
        length = len(search_mechanisms)
        if length > 0:
            searchable_result.test_status = 'pass'
            if length == 2:
                searchable_score.earned = searchable_sc
            if length == 1:
                searchable_score.earned = searchable_sc - 1
        else:
            self.logger.warning('NO search mechanism supported')

        searchable_result.score = searchable_score
        searchable_output.search_mechanisms = search_mechanisms
        searchable_result.output = searchable_output

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
        data_file_list = []

        #TODO: format may be specified in the metadata. but the data content uri is missing. will this pass the test?
        if not self.content_identifier: #self.content_identifier only includes uris that are accessible
            contents = self.metadata_merged.get('object_content_identifier')
            unique_types = []
            if contents:
                for c in contents:
                    if c.get('type'):
                        unique_types.append(c.get('type'))
                self.logger.info('FsF-R1.3-02D : File format(s) specified - {}'.format(list(set(unique_types))))

        mime_url_pair = {}
        if len(self.content_identifier) > 0:
            content_urls = [item.get('url') for item in self.content_identifier]
            self.logger.info('FsF-R1.3-02D : Data content identifier provided - {}'.format(content_urls))
            for data_file in self.content_identifier:
                mime_type = data_file.get('type')
                if data_file.get('url') is not None:
                    if mime_type is None or mime_type in ['application/octet-stream']:
                        self.logger.info('FsF-R1.3-02D : Guessing  the type of a file based on its filename or URL - {}'.format(data_file.get('url')))
                        # if mime type not given try to guess it based on the file name
                        guessed_mime_type=mimetypes.guess_type(data_file.get('url'))
                        self.logger.info('FsF-R1.3-02D : Guess return value - {}'.format(guessed_mime_type))
                        mime_type=guessed_mime_type[0] #the return value is a tuple (type, encoding) where type is None if the type can’t be guessed

                    if mime_type:
                        if mime_type in FAIRCheck.ARCHIVE_MIMETYPES: #check archive&compress media type
                            self.logger.warning('FsF-R1.3-02D : Archiving/compression format specified - {}'.format(mime_type))
                            # exclude archieve format
                            self.tika_content_types_list = [n for n in self.tika_content_types_list if n not in FAIRCheck.ARCHIVE_MIMETYPES]
                            self.logger.info('FsF-R1.3-02D : Extracted file formats - {}'.format(self.tika_content_types_list))
                            for t in self.tika_content_types_list:
                                mime_url_pair[t] = data_file.get('url')
                        else:
                            mime_url_pair[mime_type] = data_file.get('url')

            #TODO: change output type instead of is_long_term_format etc use:
            # is_prefered_format: boolean
            # type: ['long term format','science format']
            # domain: list of scientific domains, default: 'General'
            # FILE FORMAT CHECKS....
            # check if format is a scientific one:
            for mimetype, url in mime_url_pair.items():
                data_file_output = DataFileFormatOutputInner()
                preferance_reason = []
                subject_area = []
                if mimetype in FAIRCheck.SCIENCE_FILE_FORMATS:
                    if FAIRCheck.SCIENCE_FILE_FORMATS.get(mimetype) == 'Generic':
                        subject_area.append('General')
                        preferance_reason.append('generic science format')
                    else:
                        subject_area.append(FAIRCheck.SCIENCE_FILE_FORMATS.get(mimetype))
                        preferance_reason.append('science format')
                    data_file_output.is_preferred_format= True
                # check if long term format
                if mimetype in FAIRCheck.LONG_TERM_FILE_FORMATS:
                    preferance_reason.append('long term format')
                    subject_area.append('General')
                    data_file_output.is_preferred_format = True
                #check if open format
                if mimetype in FAIRCheck.OPEN_FILE_FORMATS:
                    preferance_reason.append('open format')
                    subject_area.append('General')
                    data_file_output.is_preferred_format = True
                #generic text/xml/json file check
                if re.search(text_format_regex,mimetype):
                    preferance_reason.extend(['long term format','open format','generic science format'])
                    subject_area.append('General')
                    data_file_output.is_preferred_format= True

                data_file_output.mime_type = mimetype
                data_file_output.file_uri = url
                data_file_output.preference_reason = list(set(preferance_reason))
                data_file_output.subject_areas = list(set(subject_area))
                data_file_list.append(data_file_output)

            if len(data_file_list) >0 :
                data_file_format_score.earned = 1
                data_file_format_result.test_status = 'pass'
        else:
            self.logger.warning('FsF-R1.3-02D : Could not perform file format checks as data content identifier(s) unavailable/inaccesible')
            data_file_format_result.test_status='fail'

        data_file_format_output = data_file_list
        data_file_format_result.output = data_file_format_output
        data_file_format_result.score = data_file_format_score
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
        if self.namespace_uri:
            self.namespace_uri = list(set(self.namespace_uri))
        # ============== retrieve community standards by collected namespace uris
        if len(self.namespace_uri) > 0:
            no_match = []
            self.logger.info('FsF-R1.3-01M : Namespaces included in the metadata - {}'.format(self.namespace_uri))
            for std_ns in self.namespace_uri:
                std_ns_temp = self.lookup_metadatastandard_by_uri(std_ns)
                #if std_ns_temp in FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS:
                if std_ns_temp:
                    subject = FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS.get(std_ns_temp).get('subject_areas')
                    std_name= FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS.get(std_ns_temp).get('title')
                    if subject and all(elem == "Multidisciplinary" for elem in subject):
                        self.logger.info('FsF-R1.3-01M : Skipped non-disciplinary standard found through namespaces - {}'.format(std_ns))
                    else:
                        nsout = CommunityEndorsedStandardOutputInner()
                        nsout.metadata_standard = std_name #use here original standard uri detected
                        nsout.subject_areas = subject
                        nsout.urls = [subject]
                        standards_detected.append(nsout)
                else:
                    no_match.append(std_ns)
            if len(no_match)>0:
                self.logger.info('FsF-R1.3-01M : The following standards found through namespaces are excluded as they are not listed in RDA metadata catalog - {}'.format(no_match))

        # ============== use standards listed in the re3data record if no metadata is detected from oai-pmh
        if len(self.community_standards) > 0:
            if len(standards_detected) == 0:
                self.logger.info('FsF-R1.3-01M : Use re3data the source of metadata standard(s)')
                for s in self.community_standards:
                    standard_found = self.lookup_metadatastandard_by_name(s)
                    if standard_found:
                        subject = FAIRCheck.COMMUNITY_STANDARDS.get(standard_found).get('subject_areas')
                        if subject and all(elem == "Multidisciplinary" for elem in subject):
                            self.logger.info('FsF-R1.3-01M : Skipped non-disciplinary standard - {}'.format(s))
                        else:
                            out = CommunityEndorsedStandardOutputInner()
                            out.metadata_standard = s
                            out.subject_areas = FAIRCheck.COMMUNITY_STANDARDS.get(standard_found).get('subject_areas')
                            out.urls = FAIRCheck.COMMUNITY_STANDARDS.get(standard_found).get('urls')
                            standards_detected.append(out)
            else:
                self.logger.info('FsF-R1.3-01M : Metadata standard(s) that are listed in re3data are excluded from the assessment output.')
        else:
            self.logger.warning('FsF-R1.3-01M : NO metadata standard(s) of the reposiroty specified in re3data')

        if standards_detected:
            communitystd_score.earned = communitystd_sc
            communitystd_result.test_status = 'pass'
        else:
            self.logger.warning('FsF-R1.3-01M : Unable to determine community standard(s)')

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

    def lookup_metadatastandard_by_uri(self, value):
        found = None
        # get standard uri with the highest matching percentage using fuzzywuzzy
        highest = process.extractOne(value, FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS_LIST, scorer=fuzz.token_sort_ratio)
        if highest[1] > 90:
            found = highest[0]
        return found

    def check_data_provenance(self):
        self.count += 1
        data_provenance_identifier = 'FsF-R1.2-01M'
        data_provenance_name = FAIRCheck.METRICS.get(data_provenance_identifier).get('metric_name')
        data_provenance_sc = int(FAIRCheck.METRICS.get(data_provenance_identifier).get('total_score'))
        data_provenance_score = FAIRResultCommonScore(total=data_provenance_sc)
        data_provenance_result = DataProvenance(id=self.count, metric_identifier=data_provenance_identifier,
                                                 metric_name=data_provenance_name)
        data_provenance_output = DataProvenanceOutput()
        score = 0
        has_creation_provenance = False
        provenance_elements = []
        provenance_namespaces=['http://www.w3.org/ns/prov#','http://purl.org/pav/']
        provenance_status = 'fail'

        provenance_metadata_output = DataProvenanceOutputInner()
        provenance_metadata_output.provenance_metadata = []
        provenance_metadata_output.is_available = False

        for md in self.metadata_merged:
            if md in Mapper.PROVENANCE_MAPPING.value:
                provenance_metadata_output.is_available = True
                provenance_metadata_output.provenance_metadata.append(
                    { 'prov_o_mapping': Mapper.PROVENANCE_MAPPING.value.get(md),'metadata_element': md,'metadata_value': self.metadata_merged.get(md)}
                )

        relateds = self.metadata_merged.get('related_resources')
        if isinstance(relateds, list):
            for rm in relateds:
                if rm.get('relation_type') in Mapper.PROVENANCE_MAPPING.value:
                    provenance_metadata_output.provenance_metadata.append(
                        {'prov_o_mapping': Mapper.PROVENANCE_MAPPING.value.get(rm.get('relation_type')), 'metadata_element': 'related.'+str(rm.get('relation_type')),
                        'metadata_value': rm.get('related_resource')}
                    )

        if provenance_metadata_output.is_available:
            self.logger.info('FsF-R1.2-01M : Found data creation-related provenance information')
            provenance_status = 'pass'
            score=score+1
        data_provenance_output.provenance_metadata_included = provenance_metadata_output

        #structured provenance metadata available
        structured_metadata_output = DataProvenanceOutputInner()
        structured_metadata_output.provenance_metadata = []
        structured_metadata_output.is_available = False
        used_provenance_namespace = list(set(provenance_namespaces).intersection(set(self.namespace_uri)))
        if used_provenance_namespace:
            score=score+1
            structured_metadata_output.is_available = True
            for used_prov_ns in used_provenance_namespace:
                structured_metadata_output.provenance_metadata.append({'namespace': used_prov_ns})
            self.logger.info('FsF-R1.2-01M : Found use of dedicated provenance ontologies')
        else:
            self.logger.warning('FsF-R1.2-01M : Formal provenance metadata is unavailable')
        data_provenance_output.structured_provenance_available = structured_metadata_output

        if score >= 1:
            provenance_status = 'pass'
        data_provenance_result.test_status=provenance_status
        data_provenance_score.earned = score
        data_provenance_result.output = data_provenance_output
        data_provenance_result.score = data_provenance_score
        if self.isDebug:
            data_provenance_result.test_debug = self.msg_filter.getMessage(data_provenance_identifier)
        return data_provenance_result.to_dict()

    def check_data_content_metadata(self):
        self.count+=1
        data_content_metadata_identifier = 'FsF-R1-01MD'
        data_content_metadata_name = FAIRCheck.METRICS.get(data_content_metadata_identifier).get('metric_name')
        data_content_metadata_sc = int(FAIRCheck.METRICS.get(data_content_metadata_identifier).get('total_score'))
        data_content_metadata_score = FAIRResultCommonScore(total=data_content_metadata_sc)
        data_content_metadata_result = DataContentMetadata(id=self.count, metric_identifier=data_content_metadata_identifier, metric_name=data_content_metadata_name)
        data_content_metadata_output = DataContentMetadataOutput()
        data_content_descriptors = []
        test_data_content_text = None
        test_data_content_url = None
        test_status = 'fail'
        score = 0

        self.logger.info('FsF-R1-01MD : Object landing page accessible status - {}'.format(self.isMetadataAccessible))

        # 1. check resource type #TODO: resource type collection might be classified as 'dataset'
        resource_type = self.metadata_merged.get('object_type')
        if resource_type:
            self.logger.info('FsF-R1-01MD : Resource type specified - {}'.format(resource_type))
            data_content_metadata_output.object_type = resource_type
            score += 1
        else:
            self.logger.warning('FsF-R1-01MD : NO resource type specified ')

        # 2. initially verification is restricted to the first file and only use object content uri that is accessible (self.content_identifier)
        if isinstance(self.content_identifier, list):
            content_uris = [d['url'] for d in self.content_identifier if 'url' in d]
            content_length = len(self.content_identifier)
            if content_length > 0:
                self.logger.info('FsF-R1-01MD : Number of data content URI(s) specified - {}'.format(content_length))
                test_data_content_url = self.content_identifier[-1].get('url')
                self.logger.info('FsF-R1-01MD : Selected content file to be analyzed - {}'.format(test_data_content_url))
                try:
                    # Use Tika to parse the file
                    parsedFile = parser.from_file(test_data_content_url)
                    status = parsedFile.get("status")
                    tika_content_types = parsedFile.get("metadata").get('Content-Type')
                    if isinstance(tika_content_types, list):
                        self.tika_content_types_list = list(set(i.split(';')[0] for i in tika_content_types))
                    else:
                        content_types_str = tika_content_types.split(';')[0]
                        self.tika_content_types_list.append(content_types_str)

                    # Extract the text content from the parsed file and convert to string
                    self.logger.info('{0} : File request status code {1}'.format(data_content_metadata_identifier, status))
                    parsed_content = parsedFile["content"]
                    test_data_content_text = str(parsed_content)
                    # Escape any slash # test_data_content_text = parsed_content.replace('\\', '\\\\').replace('"', '\\"')
                    if test_data_content_text:
                        parsed_files = parsedFile.get("metadata").get('resourceName')
                        self.logger.info('FsF-R1-01MD : Succesfully parsed data file(s) - {}'.format(parsed_files))
                except Exception as e:
                    self.logger.warning('{0} : Could not retrive/parse content object - {1}'.format(data_content_metadata_identifier, e))
            else:
                self.logger.warning('FsF-R1-01MD : NO data object content available/accessible to perform file descriptors (type and size) tests')

        # 3. check file type and size descriptors of parsed data file only (ref:test_data_content_url)
        if test_data_content_url:
            descriptors = ['type','size']  # default keys ['url', 'type', 'size', 'profile', 'header_content_type', 'header_content_length']
            data_object = next(item for item in self.metadata_merged.get('object_content_identifier') if item["url"] == test_data_content_url)
            missing_descriptors = []
            for d in descriptors:
                type = 'file '+ d
                if d in data_object.keys() and data_object.get(d):
                    descriptor = type
                    descriptor_value = data_object.get(d)
                    matches_content = False
                    if data_object.get('header_content_type') == data_object.get('type'):  #TODO: variation of mime type (text/tsv vs text/tab-separated-values)
                        matches_content = True
                        score += 1
                    data_content_filetype_inner = DataContentMetadataOutputInner()
                    data_content_filetype_inner.descriptor = descriptor
                    data_content_filetype_inner.descriptor_value = descriptor_value
                    data_content_filetype_inner.matches_content = matches_content
                    data_content_descriptors.append(data_content_filetype_inner)
                else:
                    self.logger.warning('{0} : NO {1} info available'.format(data_content_metadata_identifier, type))

        #4. check if varibles specified in the data file
        is_variable_scored = False
        if self.metadata_merged.get('measured_variable'):
            self.logger.info('FsF-R1-01MD : Found measured variables or observations (aka parameters) as content descriptor')
            if test_data_content_text:
                for variable in self.metadata_merged['measured_variable']:
                    variable_metadata_inner = DataContentMetadataOutputInner()
                    variable_metadata_inner.descriptor = 'measured_variable'
                    variable_metadata_inner.descriptor_value = variable
                    if variable in test_data_content_text: #TODO use rapidfuzz (fuzzy search)
                        #self.logger.info('FsF-R1-01MD : Measured variable found in file content - {}'.format(variable))
                        variable_metadata_inner.matches_content = True
                        if not is_variable_scored: # only increase once
                            score += 1
                            is_variable_scored = True
                    data_content_descriptors.append(variable_metadata_inner)
        else:
            self.logger.warning('FsF-R1-01MD : NO measured variables found in metadata, skip \'measured_variable\' test.')

        if score >= data_content_metadata_sc/2: # more than half of total score, consider the test as pass
            test_status = 'pass'
        data_content_metadata_output.data_content_descriptor = data_content_descriptors
        data_content_metadata_result.output = data_content_metadata_output
        data_content_metadata_score.earned = score
        data_content_metadata_result.score = data_content_metadata_score
        data_content_metadata_result.test_status = test_status
        if self.isDebug:
            data_content_metadata_result.test_debug = self.msg_filter.getMessage(data_content_metadata_identifier)
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
        elif MetaDataCollector.Sources.RDFA.value in self.metadata_sources:
            outputs.append(FormalMetadataOutputInner(serialization_format='RDFa', source='structured_data',
                                                     is_metadata_found=True))
            self.logger.info(
                '{0} : RDF Serialization found in the data page - {1}'.format(formal_meta_identifier, 'RDFa'))
            score += 1
        '''
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
        '''
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
            #self.logger.info('{0} : Check if SPARQL endpoint is available'.format(formal_meta_identifier))
            #self.sparql_endpoint = 'http://data.archaeologydataservice.ac.uk/sparql/repositories/archives' #test endpoint
            # self.sparql_endpoint = 'http://data.archaeologydataservice.ac.uk/query/' #test web sparql form
            #self.pid_url = 'http://data.archaeologydataservice.ac.uk/10.5284/1000011' #test uri
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
                self.logger.warning('{0} : NO SPARQL endpoint found through re3data based on the object URI provided'.format(formal_meta_identifier))

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
        if self.namespace_uri:
            self.namespace_uri = list(set(self.namespace_uri))
            self.namespace_uri = [x.strip() for x in self.namespace_uri]
        self.logger.info('{0} : Number of vocabulary namespaces extracted from all RDF-based metadata - {1}'.format(semanticvocab_identifier, len(self.namespace_uri)))

        # exclude white list
        excluded = []
        for n in self.namespace_uri:
            for i in self.DEFAULT_NAMESPACES:
                if n.startswith(i):
                    excluded.append(n)
        self.namespace_uri[:] = [x for x in self.namespace_uri if x not in excluded]
        if excluded:
            self.logger.info('{0} : Default vocabulary namespace(s) excluded - {1}'.format(semanticvocab_identifier, excluded))

        outputs = []
        score = 0
        test_status = 'fail'
        # test if exists in imported list, and the namespace is assumed to be active as it is tested during the LOD import.
        if self.namespace_uri:
            lod_namespaces = [d['namespace'] for d in self.VOCAB_NAMESPACES if 'namespace' in d]
            exists = list(set(lod_namespaces) & set(self.namespace_uri))
            self.logger.info(
                '{0} : Check the remaining namespace(s) exists in LOD - {1}'.format(semanticvocab_identifier, exists))
            if exists:
                score = semanticvocab_sc
                self.logger.info('{0} : Namespace matches found - {1}'.format(semanticvocab_identifier, exists))
                for e in exists:
                    outputs.append(SemanticVocabularyOutputInner(namespace=e, is_namespace_active=True))
            else:
                self.logger.warning('{0} : NO vocabulary namespace match is found'.format(semanticvocab_identifier))

            not_exists = [x for x in self.namespace_uri if x not in exists]
            if not_exists:
                self.logger.warning('{0} : Vocabulary namespace (s) specified but no match is found in LOD reference list - {1}'.format(semanticvocab_identifier, not_exists))
        else:
            self.logger.warning('{0} : NO namespaces of semantic vocabularies found in the metadata'.format(semanticvocab_identifier))

        if score > 0:
            test_status = 'pass'

        semanticvocab_result.test_status = test_status
        semanticvocab_score.earned = score
        semanticvocab_result.score = semanticvocab_score
        semanticvocab_result.output = outputs
        if self.isDebug:
            semanticvocab_result.test_debug = self.msg_filter.getMessage(semanticvocab_identifier)
        return semanticvocab_result.to_dict()

    def check_metadata_preservation(self):
        self.count += 1
        registry_bound_pid=['doi']
        preservation_identifier = 'FsF-A2-01M'
        preservation_name = FAIRCheck.METRICS.get(preservation_identifier).get('metric_name')
        preservation_sc = int(FAIRCheck.METRICS.get(preservation_identifier).get('total_score'))
        preservation_score = FAIRResultCommonScore(total=preservation_sc)
        preservation_result = MetadataPreserved(id=self.count, metric_identifier=preservation_identifier,
                                              metric_name=preservation_name)
        outputs = []
        test_status = 'fail'
        score = 0
        if self.pid_scheme:
            if self.pid_scheme in registry_bound_pid:
                test_status = 'pass'
                outputs.append(MetadataPreservedOutput(metadata_preservation_method='datacite'))
                score = 1
                self.logger.info(
                    '{0} : Metadata registry bound PID system used: '+self.pid_scheme.format(preservation_identifier))
            else:
                self.logger.info(
                    '{0} : NO metadata registry bound PID system used'.format(preservation_identifier))
        preservation_score.earned = score
        preservation_result.score = preservation_score
        preservation_result.output = outputs
        preservation_result.test_status = test_status
        if self.isDebug:
            preservation_result.test_debug = self.msg_filter.getMessage(preservation_identifier)
        return preservation_result.to_dict()

    def check_standardised_protocol(self):
        self.count += 1
        protocol_identifier = 'FsF-A1-02MD'
        protocol_name = FAIRCheck.METRICS.get(protocol_identifier).get('metric_name')
        protocol_sc = int(FAIRCheck.METRICS.get(protocol_identifier).get('total_score'))
        protocol_score = FAIRResultCommonScore(total=protocol_sc)
        protocol_result = StandardisedProtocol(id=self.count, metric_identifier=protocol_identifier,
                                                metric_name=protocol_name)
        metadata_output = data_output = None
        metadata_required = Mapper.REQUIRED_CORE_METADATA.value
        metadata_found = {k: v for k, v in self.metadata_merged.items() if k in metadata_required}
        test_status = 'fail'
        score = 0
        if self.landing_url is not None:
            # parse the URL and return the protocol which has to be one of Internet RFC on Relative Uniform Resource Locators
            metadata_parsed_url = urlparse(self.landing_url)
            metadata_url_scheme = metadata_parsed_url.scheme

            if metadata_url_scheme in FAIRCheck.STANDARD_PROTOCOLS:
                metadata_output= {metadata_url_scheme:FAIRCheck.STANDARD_PROTOCOLS.get(metadata_url_scheme)}
                test_status = 'pass'
                score += 1
            if set(metadata_found) != set(metadata_required):
                self.logger.info(
                    '{0} : NOT all required metadata given, see: FsF-F2-01M'.format(protocol_identifier))
                #parse the URL and return the protocol which has to be one of Internet RFC on Relative Uniform Resource Locators
        else:
            self.logger.info(
                '{0} : Metadata Identifier is not actionable or protocol errors occured'.format(protocol_identifier))

        if len(self.content_identifier) > 0:
            #here we only test the first content identifier
            data_url = self.content_identifier[0].get('url')
            data_parsed_url = urlparse(data_url)
            data_url_scheme = data_parsed_url.scheme

            if data_url_scheme in FAIRCheck.STANDARD_PROTOCOLS:
                data_output = {data_url_scheme: FAIRCheck.STANDARD_PROTOCOLS.get(data_url_scheme)}
                test_status = 'pass'
                score += 1
        else:
            self.logger.info(
                '{0} : NO content (data) identifier is given in metadata'.format(protocol_identifier))

        protocol_score.earned = score
        protocol_result.score = protocol_score
        protocol_result.output = StandardisedProtocolOutput(standard_metadata_protocol=metadata_output,standard_data_protocol=data_output)
        protocol_result.test_status = test_status
        if self.isDebug:
            protocol_result.test_debug = self.msg_filter.getMessage(protocol_identifier)
        return protocol_result.to_dict()

