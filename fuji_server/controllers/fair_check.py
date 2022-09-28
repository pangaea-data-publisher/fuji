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
import io
import json
import logging, logging.handlers
import mimetypes
import re
#import urllib
import urllib.request as urllib
#from typing import List, Any
from urllib.parse import urlparse, urljoin

import extruct
#import idutils
import pandas as pd
import lxml
import rdflib
from bs4 import BeautifulSoup
from pyRdfa import pyRdfa
from rapidfuzz import fuzz
from rapidfuzz import process
import hashlib

from tldextract import extract

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
from fuji_server.harvester.metadata_harvester import MetadataHarvester

from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.metadata_collector_datacite import MetaDataCollectorDatacite
from fuji_server.helper.metadata_collector_dublincore import MetaDataCollectorDublinCore
from fuji_server.helper.metadata_collector_microdata import MetaDataCollectorMicroData
from fuji_server.helper.metadata_collector_opengraph import MetaDataCollectorOpenGraph
from fuji_server.helper.metadata_collector_ore_atom import MetaDataCollectorOreAtom
from fuji_server.helper.metadata_collector_rdf import MetaDataCollectorRdf
from fuji_server.helper.metadata_collector_schemaorg import MetaDataCollectorSchemaOrg
from fuji_server.helper.metadata_collector_xml import MetaDataCollectorXML
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.metadata_provider_csw import OGCCSWMetadataProvider
from fuji_server.helper.metadata_provider_oai import OAIMetadataProvider
from fuji_server.helper.metadata_provider_sparql import SPARQLMetadataProvider
from fuji_server.helper.metadata_provider_rss_atom import RSSAtomMetadataProvider
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.repository_helper import RepositoryHelper
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.helper.linked_vocab_helper import linked_vocab_helper


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
    SCHEMA_ORG_CONTEXT = []
    FILES_LIMIT = None
    LOG_SUCCESS = 25
    LOG_FAILURE = 35
    VALID_RESOURCE_TYPES = []
    IDENTIFIERS_ORG_DATA = {}
    GOOGLE_DATA_DOI_CACHE = []
    GOOGLE_DATA_URL_CACHE = []
    LINKED_VOCAB_INDEX = {}
    FUJI_VERSION = '2.2.0'

    def __init__(self,
                 uid,
                 test_debug=False,
                 metadata_service_url=None,
                 metadata_service_type=None,
                 use_datacite=True,
                 oaipmh_endpoint=None):
        uid_bytes = uid.encode('utf-8')
        self.test_id = hashlib.sha1(uid_bytes).hexdigest()
        #str(base64.urlsafe_b64encode(uid_bytes), "utf-8") # an id we can use for caching etc
        if isinstance(uid, str):
            uid = uid.strip()
        self.id = self.input_id = uid

        self.metadata_service_url = metadata_service_url
        self.metadata_service_type = metadata_service_type
        self.oaipmh_endpoint = oaipmh_endpoint
        self.csw_endpoint = None
        self.sparql_endpoint = None
        if self.oaipmh_endpoint:
            self.metadata_service_url = self.oaipmh_endpoint
            self.metadata_service_type = 'oai_pmh'
        if self.metadata_service_type == 'oai_pmh':
            self.oaipmh_endpoint = self.metadata_service_url
        elif self.metadata_service_type == 'ogc_csw':
            self.csw_endpoint = self.metadata_service_url
        elif self.metadata_service_type == 'sparql':
            self.sparql_endpoint = self.metadata_service_url
        self.pid_url = None  # full pid # e.g., "https://doi.org/10.1594/pangaea.906092 or url (non-pid)
        self.landing_url = None  # url of the landing page of self.pid_url
        self.origin_url = None  #the url from where all starts - in case of redirection we'll need this later on
        self.landing_html = None
        self.landing_content_type = None
        self.landing_origin = None  # schema + authority of the landing page e.g. https://www.pangaea.de
        self.signposting_header_links = []
        self.typed_links = []
        self.pid_scheme = None
        self.id_scheme = None
        self.checked_pages = []
        self.logger = logging.getLogger(self.test_id)
        self.metadata_sources = []
        self.isDebug = test_debug
        self.isLandingPageAccessible = None
        self.metadata_merged = {}
        self.metadata_unmerged = []
        self.content_identifier = []
        self.community_standards = []
        self.community_standards_uri = {}
        self.namespace_uri = []
        self.linked_namespace_uri = {}
        self.reference_elements = Mapper.REFERENCE_METADATA_LIST.value.copy(
        )  # all metadata elements required for FUJI metrics
        self.related_resources = []
        # self.test_data_content_text = None# a helper to check metadata against content
        self.rdf_graph = None

        self.rdf_collector = None
        self.use_datacite = use_datacite
        self.repeat_pid_check = False
        self.logger_message_stream = io.StringIO()
        logging.addLevelName(self.LOG_SUCCESS, 'SUCCESS')
        logging.addLevelName(self.LOG_FAILURE, 'FAILURE')

        # in case log messages shall be sent to a remote server
        self.remoteLogPath = None
        self.remoteLogHost = None
        self.weblogger = None
        if self.isDebug:
            self.logStreamHandler = logging.StreamHandler(self.logger_message_stream)
            formatter = logging.Formatter('%(message)s|%(levelname)s')
            self.logStreamHandler.setFormatter(formatter)
            self.logger.propagate = False
            self.logger.setLevel(logging.INFO)  # set to debug in testing environment
            self.logger.addHandler(self.logStreamHandler)

            if Preprocessor.remote_log_host:
                self.weblogger = logging.handlers.HTTPHandler(Preprocessor.remote_log_host, Preprocessor.remote_log_path + '?testid=' + str(self.test_id),
                                                      method='POST')
                self.webformatter = logging.Formatter('%(levelname)s - %(message)s \r\n')

        self.count = 0
        FAIRCheck.load_predata()
        #self.extruct = None
        self.extruct_result = {}
        self.tika_content_types_list = []
        self.lov_helper = linked_vocab_helper(self.LINKED_VOCAB_INDEX)
        self.auth_token = None
        self.auth_token_type = 'Basic'
        self.metadata_harvester = MetadataHarvester(self.id,use_datacite = use_datacite)

    @classmethod
    def load_predata(cls):
        cls.FILES_LIMIT = Preprocessor.data_files_limit
        if not cls.METRICS:
            cls.METRICS = Preprocessor.get_custom_metrics(
                ['metric_name', 'total_score', 'metric_tests', 'metric_number'])
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
        if not cls.SCHEMA_ORG_CONTEXT:
            cls.SCHEMA_ORG_CONTEXT = Preprocessor.get_schema_org_context()
        if not cls.VALID_RESOURCE_TYPES:
            cls.VALID_RESOURCE_TYPES = Preprocessor.get_resource_types()
        if not cls.IDENTIFIERS_ORG_DATA:
            cls.IDENTIFIERS_ORG_DATA = Preprocessor.get_identifiers_org_data()
        if not cls.LINKED_VOCAB_INDEX:
            cls.LINKED_VOCAB_INDEX = Preprocessor.get_linked_vocab_index()
        Preprocessor.set_mime_types()
        #not needed locally ... but init class variable
        #Preprocessor.get_google_data_dois()
        #Preprocessor.get_google_data_urls()

    @staticmethod
    def uri_validator(u):  # TODO integrate into request_helper.py
        try:
            r = urlparse(u)
            return all([r.scheme, r.netloc])
        except:
            return False

    def set_auth_token(self, auth_token, auth_token_type='Basic'):
        if auth_token:
            self.auth_token = auth_token
            self.metadata_harvester.auth_token = self.auth_token
        if auth_token_type:
            if auth_token_type in ['Basic','Bearer']:
                self.auth_token_type = auth_token_type
                self.metadata_harvester.auth_token_type = self.auth_token_type
            else:
                self.auth_token_type = 'Basic'


    def validate_service_url(self):
        # checks if service url and landing page url have same domain in order to avoid manipulations
        if self.metadata_service_url:
            service_url_parts = extract(self.metadata_service_url)
            landing_url_parts = extract(self.landing_url)
            service_domain = service_url_parts.domain + '.' + service_url_parts.suffix
            landing_domain = landing_url_parts.domain + '.' + landing_url_parts.suffix
            if landing_domain == service_domain:
                return True
            else:
                self.logger.warning(
                    'FsF-R1.3-01M : Service URL domain/subdomain does not match with landing page domain -: {}'.format(
                        service_domain, landing_domain))
                self.metadata_service_url, self.csw_endpoint, self.oaipmh_endpoint, self.sparql_endpoint = None, None, None, None
                return False
        else:
            return False

    def merge_metadata(self, metadict, sourceurl, method_source, format, schema='', namespaces = []):
        if not isinstance(namespaces, list):
            namespaces = [namespaces]
        if isinstance(metadict,dict):
            #self.metadata_sources.append((method_source, 'negotiated'))

            for r in metadict.keys():
                if r in self.reference_elements:
                    self.metadata_merged[r] = metadict[r]
                    self.reference_elements.remove(r)

            if metadict.get('related_resources'):
                self.related_resources.extend(metadict.get('related_resources'))
            if metadict.get('object_content_identifier'):
                self.logger.info('FsF-F3-01M : Found data links in '+str(format)+' metadata -: ' +
                                 str(metadict.get('object_content_identifier')))
            ## add: mechanism ('content negotiation', 'typed links', 'embedded')
            ## add: format namespace
            self.metadata_unmerged.append(
                    {'method' : method_source,
                     'url' : sourceurl,
                     'format' : format,
                     'schema' : schema,
                     'metadata' : metadict,
                     'namespaces' : namespaces}
            )

    def clean_metadata(self):
        data_objects = self.metadata_merged.get('object_content_identifier')
        if data_objects == {'url': None} or data_objects == [None]:
            data_objects = self.metadata_merged['object_content_identifier'] = None
        if data_objects is not None:
            if not isinstance(data_objects, list):
                self.metadata_merged['object_content_identifier'] = [data_objects]

        # TODO quick-fix to merge size information - should do it at mapper
        if 'object_content_identifier' in self.metadata_merged:
            if self.metadata_merged.get('object_content_identifier'):
                oi = 0
                for c in self.metadata_merged['object_content_identifier']:
                    if not c.get('size') and self.metadata_merged.get('object_size'):
                        c['size'] = self.metadata_merged.get('object_size')
                    # clean mime types in case these are in URI form:
                    if c.get('type'):
                        if isinstance(c['type'], list):
                            c['type'] = c['type'][0]
                            self.metadata_merged['object_content_identifier'][oi]['type'] = c['type'][0]
                        mime_parts = str(c.get('type')).split('/')
                        if len(mime_parts) > 2:
                            if mime_parts[-2] in ['application', 'audio', 'font', 'example', 'image', 'message',
                                                  'model', 'multipart', 'text', 'video']:
                                self.metadata_merged['object_content_identifier'][oi]['type'] = str(
                                    mime_parts[-2]) + '/' + str(mime_parts[-1])
                    oi += 1
        #clean empty entries
        for mk, mv in list(self.metadata_merged.items()):
            if mv == '' or mv is None:
                del self.metadata_merged[mk]

    def harvest_all_metadata(self):
        #if isinstance(extruct_metadata, dict):
        #    embedded_exists = {k: v for k, v in extruct_metadata.items() if v}
        #    self.extruct = embedded_exists.copy()

        # ========= clean merged metadata, delete all entries which are None or ''

        self.retrieve_metadata_embedded()
        self.retrieve_metadata_external()
        self.clean_metadata()

        self.logger.info('FsF-F2-01M : Type of object described by the metadata -: {}'.format(
            self.metadata_merged.get('object_type')))

        # detect api and standards
        self.retrieve_apis_standards()

        # remove duplicates
        if self.namespace_uri:
            self.namespace_uri = list(set(self.namespace_uri))


    def retrieve_apis_standards(self):
        if self.landing_url is not None:
            self.logger.info('FsF-R1.3-01M : Retrieving API and Standards')
            if self.use_datacite:
                client_id = self.metadata_merged.get('datacite_client')
                self.logger.info('FsF-R1.3-01M : re3data/datacite client id -: {}'.format(client_id))
            else:
                client_id = None
                self.logger.warning(
                    '{} : Datacite support disabled, therefore skipping standards identification using in re3data record'
                    .format(
                        'FsF-R1.3-01M',
                    ))

            if self.metadata_service_url not in [None, '']:
                self.logger.info('FsF-R1.3-01M : Metadata service endpoint (' + str(self.metadata_service_type) +
                                 ') provided as part of the request -: ' + str(self.metadata_service_url))
            #else:
            #check re3data always instead...
            if self.use_datacite:
                self.logger.info(
                    'FsF-R1.3-01M : Trying to retrieve metadata info from re3data/datacite services using client id -: '
                    + str(client_id))
                #find endpoint via datacite/re3data if pid is provided
                #print(client_id ,self.pid_scheme)
                if client_id and self.pid_scheme:
                    repoHelper = RepositoryHelper(client_id, self.pid_scheme, logger=self.logger.name,landingpage=self.landing_url)
                    repoHelper.lookup_re3data()
                    if not self.metadata_service_url:
                        self.logger.info('{} : Inferring endpoint information through re3data/datacite services'.format(
                            'FsF-R1.3-01M'))
                        self.oaipmh_endpoint = repoHelper.getRe3MetadataAPIs().get('OAI-PMH')
                        self.sparql_endpoint = repoHelper.getRe3MetadataAPIs().get('SPARQL')
                    self.community_standards.extend(repoHelper.getRe3MetadataStandards())
                    self.logger.info('{} : Metadata standards listed in re3data record -: {}'.format(
                        'FsF-R1.3-01M', self.community_standards))
            else:
                self.logger.info(
                    'FsF-R1.3-01M : Skipped re3data metadata standards query since Datacite support is disabled by user'
                )
                # verify the service url by domain matching
            self.validate_service_url()
            # retrieve metadata standards info from oai-pmh
            if self.oaipmh_endpoint:
                self.logger.info('{} : Use OAI-PMH endpoint to retrieve standards used by the repository -: {}'.format(
                    'FsF-R1.3-01M', self.oaipmh_endpoint))
                if (self.uri_validator(self.oaipmh_endpoint)):
                    oai_provider = OAIMetadataProvider(endpoint=self.oaipmh_endpoint,
                                                       logger=self.logger,
                                                       metric_id='FsF-R1.3-01M')
                    self.community_standards_uri = oai_provider.getMetadataStandards()
                    self.namespace_uri.extend(oai_provider.getNamespaces())
                    stds = None
                    if self.community_standards_uri:
                        stds = list(self.community_standards_uri.keys())
                        self.logger.log(
                            self.LOG_SUCCESS,
                            '{} : Found disciplinary standards that are listed in OAI-PMH endpoint -: {}'.format(
                                'FsF-R1.3-01M', stds))
                else:
                    self.logger.info('{} : Invalid endpoint'.format('FsF-R1.3-01M'))
            else:
                self.logger.warning('{} : NO valid OAI-PMH endpoint found'.format('FsF-R1.3-01M'))

            # retrieve metadata standards info from OGC CSW
            if self.csw_endpoint:
                self.logger.info('{} : Use OGC CSW endpoint to retrieve standards used by the repository -: {}'.format(
                    'FsF-R1.3-01M', self.oaipmh_endpoint))
                if (self.uri_validator(self.csw_endpoint)):
                    csw_provider = OGCCSWMetadataProvider(endpoint=self.csw_endpoint,
                                                          logger=self.logger,
                                                          metric_id='FsF-R1.3-01M')
                    self.community_standards_uri = csw_provider.getMetadataStandards()
                    self.namespace_uri.extend(csw_provider.getNamespaces())
                    stds = None
                    if self.community_standards_uri:
                        stds = list(self.community_standards_uri.keys())
                        self.logger.log(
                            self.LOG_SUCCESS,
                            '{} : Found disciplinary standards that are listed in OGC CSW endpoint -: {}'.format(
                                'FsF-R1.3-01M', stds))
                else:
                    self.logger.info('{} : Invalid OGC CSW endpoint'.format('FsF-R1.3-01M'))

            # retrieve metadata standards info from SPARQL endpoint
            if self.sparql_endpoint:
                self.logger.info('{} : Use SPARQL endpoint to retrieve standards used by the repository -: {}'.format(
                    'FsF-R1.3-01M', self.sparql_endpoint))
                if (self.uri_validator(self.sparql_endpoint)):
                    sparql_provider = SPARQLMetadataProvider(endpoint=self.sparql_endpoint,
                                                             logger=self.logger,
                                                             metric_id='FsF-R1.3-01M')
                    self.community_standards_uri = sparql_provider.getMetadataStandards()
                    self.namespace_uri.extend(sparql_provider.getNamespaces())
                    stds = None
                    if self.community_standards_uri:
                        stds = list(self.community_standards_uri.keys())
                        self.logger.log(
                            self.LOG_SUCCESS,
                            '{} : Found disciplinary standards that are listed in SPARQL endpoint -: {}'.format(
                                'FsF-R1.3-01M', stds))
                else:
                    self.logger.info('{} : Invalid SPARQL endpoint'.format('FsF-R1.3-01M'))

        else:
            self.logger.warning(
                '{} : Skipped external ressources (e.g. OAI, re3data) checks since landing page could not be resolved'.
                format('FsF-R1.3-01M'))

    def retrieve_metadata_embedded(self):
        self.metadata_harvester.retrieve_metadata_embedded()
        self.metadata_unmerged.extend( self.metadata_harvester.metadata_unmerged)
        self.metadata_merged.update( self.metadata_harvester.metadata_merged)
        self.repeat_pid_check =  self.metadata_harvester.repeat_pid_check
        self.namespace_uri.extend( self.metadata_harvester.namespace_uri)
        self.metadata_sources.extend( self.metadata_harvester.metadata_sources)
        self.linked_namespace_uri.update( self.metadata_harvester.linked_namespace_uri)
        self.related_resources.extend( self.metadata_harvester.related_resources)
        self.landing_url =  self.metadata_harvester.landing_url
        self.origin_url =  self.metadata_harvester.origin_url
        self.pid_url =  self.metadata_harvester.pid_url
        self.pid_scheme = self.metadata_harvester.pid_scheme

    def retrieve_metadata_external(self, target_url = None, repeat_mode = False):
        self.metadata_harvester.retrieve_metadata_external(target_url, repeat_mode = repeat_mode)
        self.metadata_unmerged.extend( self.metadata_harvester.metadata_unmerged)
        self.metadata_merged.update( self.metadata_harvester.metadata_merged)
        self.repeat_pid_check =  self.metadata_harvester.repeat_pid_check
        self.namespace_uri.extend( self.metadata_harvester.namespace_uri)
        self.metadata_sources.extend( self.metadata_harvester.metadata_sources)
        self.linked_namespace_uri.update( self.metadata_harvester.linked_namespace_uri)
        self.related_resources.extend( self.metadata_harvester.related_resources)

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
        highest = process.extractOne(value,
                                     FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS_LIST,
                                     scorer=fuzz.token_sort_ratio)
        if highest:
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
        self.metadata_harvester.get_signposting_object_identifier()
        return self.check_unique_identifier(), self.check_persistent_identifier()

    def check_minimal_metatadata(self, include_embedded=True):
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
        semantic_vocabulary_check.set_metric('FsF-I2-01M', metrics=FAIRCheck.METRICS)
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
        standardised_protocol_metadata_check = FAIREvaluatorStandardisedProtocolMetadata(self)
        standardised_protocol_metadata_check.set_metric('FsF-A1-02M', metrics=FAIRCheck.METRICS)
        return standardised_protocol_metadata_check.getResult()

    def raise_warning_if_javascript_page(self, response_content):
        # check if javascript generated content only:
        try:
            soup = BeautifulSoup(response_content, features='html.parser')
            script_content = soup.findAll('script')
            for script in soup(['script', 'style', 'title', 'noscript']):
                script.extract()

            text_content = soup.get_text(strip=True)
            if (len(str(script_content)) > len(str(text_content))) and len(text_content) <= 150:
                self.logger.warning('FsF-F1-02D : Landing page seems to be JavaScript generated, could not detect enough content')
        except Exception as e:
            pass

    def get_log_messages_dict(self):
        logger_messages = {}
        self.logger_message_stream.seek(0)
        for log_message in self.logger_message_stream.readlines():
            if log_message.startswith('FsF-'):
                m = log_message.split(':', 1)
                metric = m[0].strip()
                message_n_level = m[1].strip().split('|', 1)
                if len(message_n_level) > 1:
                    level = message_n_level[1]
                else:
                    level = 'INFO'
                message = message_n_level[0]
                if metric not in logger_messages:
                    logger_messages[metric] = []
                if message not in logger_messages[metric]:
                    logger_messages[metric].append(level.replace('\n', '') + ': ' + message.strip())
        self.logger_message_stream = io.StringIO

        return logger_messages

    def get_assessment_summary(self, results):
        status_dict = {'pass': 1, 'fail': 0}
        maturity_dict = Mapper.MATURITY_LEVELS.value
        summary_dict = {
            'fair_category': [],
            'fair_principle': [],
            'score_earned': [],
            'score_total': [],
            'maturity': [],
            'status': []
        }
        for res_k, res_v in enumerate(results):
            metric_match = re.search(r'^FsF-(([FAIR])[0-9](\.[0-9])?)-', res_v['metric_identifier'])
            if metric_match.group(2) is not None:
                fair_principle = metric_match[1]
                fair_category = metric_match[2]
                earned_maturity = res_v['maturity']
                #earned_maturity = [k for k, v in maturity_dict.items() if v == res_v['maturity']][0]
                summary_dict['fair_category'].append(fair_category)
                summary_dict['fair_principle'].append(fair_principle)
                #An easter egg for Mustapha
                if self.input_id in ['https://www.rd-alliance.org/users/mustapha-mokrane','https://www.rd-alliance.org/users/ilona-von-stein']:
                    summary_dict['score_earned'].append(res_v['score']['total'])
                    summary_dict['maturity'].append(3)
                    summary_dict['status'].append(1)
                else:
                    summary_dict['score_earned'].append(res_v['score']['earned'])
                    summary_dict['maturity'].append(earned_maturity)
                    summary_dict['status'].append(status_dict.get(res_v['test_status']))
                summary_dict['score_total'].append(res_v['score']['total'])

        sf = pd.DataFrame(summary_dict)
        summary = {'score_earned': {}, 'score_total': {}, 'score_percent': {}, 'status_total': {}, 'status_passed': {}}

        summary['score_earned'] = sf.groupby(by='fair_category')['score_earned'].sum().to_dict()
        summary['score_earned'].update(sf.groupby(by='fair_principle')['score_earned'].sum().to_dict())
        summary['score_earned']['FAIR'] = round(float(sf['score_earned'].sum()), 2)

        summary['score_total'] = sf.groupby(by='fair_category')['score_total'].sum().to_dict()
        summary['score_total'].update(sf.groupby(by='fair_principle')['score_total'].sum().to_dict())
        summary['score_total']['FAIR'] = round(float(sf['score_total'].sum()), 2)

        summary['score_percent'] = (round(
            sf.groupby(by='fair_category')['score_earned'].sum() / sf.groupby(by='fair_category')['score_total'].sum() *
            100, 2)).to_dict()
        summary['score_percent'].update((round(
            sf.groupby(by='fair_principle')['score_earned'].sum() /
            sf.groupby(by='fair_principle')['score_total'].sum() * 100, 2)).to_dict())
        summary['score_percent']['FAIR'] = round(float(sf['score_earned'].sum() / sf['score_total'].sum() * 100), 2)

        summary['maturity'] = sf.groupby(by='fair_category')['maturity'].apply(
            lambda x: 1 if x.mean() < 1 and x.mean() > 0 else round(x.mean())).to_dict()
        summary['maturity'].update(
            sf.groupby(by='fair_principle')['maturity'].apply(
                lambda x: 1 if x.mean() < 1 and x.mean() > 0 else round(x.mean())).to_dict())
        total_maturity = 0
        for fair_index in ['F', 'A', 'I', 'R']:
            total_maturity += summary['maturity'][fair_index]
        summary['maturity']['FAIR'] = round(
            float(1 if total_maturity / 4 < 1 and total_maturity / 4 > 0 else total_maturity / 4), 2)

        summary['status_total'] = sf.groupby(by='fair_principle')['status'].count().to_dict()
        summary['status_total'].update(sf.groupby(by='fair_category')['status'].count().to_dict())
        summary['status_total']['FAIR'] = int(sf['status'].count())

        summary['status_passed'] = sf.groupby(by='fair_principle')['status'].sum().to_dict()
        summary['status_passed'].update(sf.groupby(by='fair_category')['status'].sum().to_dict())
        summary['status_passed']['FAIR'] = int(sf['status'].sum())
        return summary

    #in case experimental mime types are detected add mime types without x. or x. prefix
    def extend_mime_type_list(self, mime_list):
        if isinstance(mime_list, str):
            mime_list = [mime_list]
        for mime in mime_list:
            xm = re.split(r'/(?:[xX][-\.])?', mime)
            if len(xm) == 2:
                if str(xm[0] + '/' + xm[1]) not in mime_list:
                    mime_list.append(str(xm[0] + '/' + xm[1]))
        return mime_list
