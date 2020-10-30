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

from fuji_server.evaluators.fair_evaluator_license import FAIREvaluatorLicense
from fuji_server.evaluators.fair_evaluator_data_access_level import FAIREvaluatorDataAccessLevel
from fuji_server.evaluators.fair_evaluator_persistent_identifier import FAIREvaluatorPersistentIdentifier
from fuji_server.evaluators.fair_evaluator_unique_identifier import FAIREvaluatorUniqueIdentifier
from fuji_server.evaluators.fair_evaluator_minimal_metadata import FAIREvaluatorCoreMetadata
from fuji_server.evaluators.fair_evaluator_content_included import FAIREvaluatorContentIncluded
from fuji_server.evaluators.fair_evaluator_related_resources import FAIREvaluatorRelatedResources
from fuji_server.evaluators.fair_evaluator_searchable import FAIREvaluatorSearchable
from fuji_server.evaluators.fair_evaluator_file_format import FAIREvaluatorFileFormat
from fuji_server.evaluators.fair_evaluator_data_provenance import FAIREvaluatorDataProvenance
from fuji_server.evaluators.fair_evaluator_data_content_metadata import FAIREvaluatorDataContentMetadata
from fuji_server.evaluators.fair_evaluator_formal_metadata import FAIREvaluatorFormalMetadata
from fuji_server.evaluators.fair_evaluator_semantic_vocabulary import FAIREvaluatorSemanticVocabulary
from fuji_server.evaluators.fair_evaluator_metadata_preservation import FAIREvaluatorMetadataPreserved
from fuji_server.evaluators.fair_evaluator_community_metadata import FAIREvaluatorCommunityMetadata
from fuji_server.evaluators.fair_evaluator_standardised_protocol_data import FAIREvaluatorStandardisedProtocolData
from fuji_server.evaluators.fair_evaluator_standardised_protocol_metadata import FAIREvaluatorStandardisedProtocolMetadata

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
from fuji_server.models.standardised_protocol_data import StandardisedProtocolData
from fuji_server.models.standardised_protocol_data_output import StandardisedProtocolDataOutput


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
            self.logger.info('FsF-F2-01M : Checking for DublinCore metadata')
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
        highest = process.extractOne(value, FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS_LIST,
                                     scorer=fuzz.token_sort_ratio)
        if highest[1] > 90:
            found = highest[0]
        return found

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

    def check_minimal_metatadata(self):
        core_metadata_check = FAIREvaluatorCoreMetadata(self)
        core_metadata_check.set_metric('FsF-F2-01M', metrics=FAIRCheck.METRICS)
        return core_metadata_check.getResult()

    def check_content_identifier_included(self):
        content_included_check = FAIREvaluatorContentIncluded(self)
        content_included_check.set_metric('FsF-F3-01M', metrics=FAIRCheck.METRICS)
        return content_included_check.getResult()

    def check_data_access_level(self):
        data_access_level_check = FAIREvaluatorDataAccessLevel(self)
        data_access_level_check.set_metric('FsF-A1-01M', metrics=FAIRCheck.METRICS)
        return data_access_level_check.getResult()

    def check_license(self):
        license_check = FAIREvaluatorLicense(self)
        license_check.set_metric('FsF-R1.1-01M', metrics=FAIRCheck.METRICS)
        return license_check.getResult()

    def check_relatedresources(self):
        related_check = FAIREvaluatorRelatedResources(self)
        related_check.set_metric('FsF-I3-01M', metrics=FAIRCheck.METRICS)
        return related_check.getResult()

    def check_searchable(self):
        searchable_check = FAIREvaluatorSearchable(self)
        searchable_check.set_metric('FsF-F4-01M', metrics=FAIRCheck.METRICS)
        return searchable_check.getResult()

    def check_data_file_format(self):
        data_file_check = FAIREvaluatorFileFormat(self)
        data_file_check.set_metric('FsF-R1.3-02D', metrics=FAIRCheck.METRICS)
        return data_file_check.getResult()

    def check_community_metadatastandards(self):
        community_metadata_check = FAIREvaluatorCommunityMetadata(self)
        community_metadata_check.set_metric('FsF-R1.3-01M', metrics=FAIRCheck.METRICS)
        return community_metadata_check.getResult()

    def check_data_provenance(self):
        data_prov_check = FAIREvaluatorDataProvenance(self)
        data_prov_check.set_metric('FsF-R1.2-01M', metrics=FAIRCheck.METRICS)
        return data_prov_check.getResult()

    def check_data_content_metadata(self):
        data_content_metadata_check = FAIREvaluatorDataContentMetadata(self)
        data_content_metadata_check.set_metric('FsF-R1-01MD', metrics=FAIRCheck.METRICS)
        return data_content_metadata_check.getResult()

    def check_formal_metadata(self):
        formal_metadata_check = FAIREvaluatorFormalMetadata(self)
        formal_metadata_check.set_metric('FsF-I1-01M', metrics=FAIRCheck.METRICS)
        return formal_metadata_check.getResult()

    def check_semantic_vocabulary(self):
        semantic_vocabulary_check = FAIREvaluatorSemanticVocabulary(self)
        semantic_vocabulary_check.set_metric('FsF-I1-02M', metrics=FAIRCheck.METRICS)
        return semantic_vocabulary_check.getResult()

    def check_metadata_preservation(self):
        metadata_preserved_check = FAIREvaluatorMetadataPreserved(self)
        metadata_preserved_check.set_metric('FsF-A2-01M', metrics=FAIRCheck.METRICS)
        return metadata_preserved_check.getResult()

    def check_standardised_protocol_data(self):
        standardised_protocol_check = FAIREvaluatorStandardisedProtocolData(self)
        standardised_protocol_check.set_metric('FsF-A1-03D', metrics=FAIRCheck.METRICS)
        return standardised_protocol_check.getResult()

    def check_standardised_protocol_metadata(self):
        standardised_protocol_check = FAIREvaluatorStandardisedProtocolMetadata(self)
        standardised_protocol_check.set_metric('FsF-A1-02M', metrics=FAIRCheck.METRICS)
        return standardised_protocol_check.getResult()
