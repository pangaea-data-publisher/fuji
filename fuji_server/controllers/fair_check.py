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
from typing import List, Any
from urllib.parse import urlparse, urljoin

import extruct
import idutils
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
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


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
    VALID_RESOURCE_TYPES = []
    IDENTIFIERS_ORG_DATA = {}
    GOOGLE_DATA_DOI_CACHE = []
    GOOGLE_DATA_URL_CACHE = []
    LINKED_VOCAB_INDEX = {}
    FUJI_VERSION = '2.0.2'

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
        self.isMetadataAccessible = None
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
                    'FsF-R1.3-01M', self.oaipmh_endpoint))
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

    def retrieve_metadata_embedded_extruct(self):
        # extract contents from the landing page using extruct, which returns a dict with
        # keys 'json-ld', 'microdata', 'microformat','opengraph','rdfa'
        syntaxes = ['microdata', 'opengraph', 'json-ld']
        extracted = {}
        if self.landing_html:
            try:
                extruct_target = self.landing_html.encode('utf-8')
            except Exception as e:
                extruct_target = self.landing_html
                pass
            try:
                self.logger.info('%s : Trying to identify EMBEDDED  Microdata, OpenGraph or JSON -: %s' %
                                 ('FsF-F2-01M', self.landing_url))
                extracted = extruct.extract(extruct_target, syntaxes=syntaxes)
            except Exception as e:
                extracted = {}
                self.logger.warning('%s : Failed to parse HTML embedded microdata or JSON -: %s' %
                                    ('FsF-F2-01M', self.landing_url + ' ' + str(e)))
            if isinstance(extracted, dict):
                extracted = dict([(k, v) for k, v in extracted.items() if len(v) > 0])
                if len(extracted) == 0:
                    extracted = {}
        else:
            print('NO LANDING HTML')
        return extracted

    def retrieve_metadata_embedded(self):
        # ======= RETRIEVE METADATA FROM LANDING PAGE =======
        response_status = None
        try:
            self.logger.info('FsF-F2-01M : Trying to resolve input URL -: ' + str(self.id))
            # check if is PID in this case complete to URL
            input_url = None
            extruct_metadata = {}
            input_urlscheme = urlparse(self.id).scheme
            if input_urlscheme not in self.STANDARD_PROTOCOLS:
                idhelper = IdentifierHelper(self.id)
                self.pid_url = input_url = idhelper.get_identifier_url()
            else:
                input_url = self.id
            if input_url:
                requestHelper = RequestHelper(input_url, self.logger)
                requestHelper.setAcceptType(AcceptTypes.default)  # request
                neg_source, landingpage_html = requestHelper.content_negotiate('FsF-F1-02D', ignore_html=False)
                if not 'html' in str(requestHelper.content_type):
                    self.logger.info('FsF-F2-01M :Content type is ' + str(requestHelper.content_type) +
                                     ', therefore skipping Embedded metadata (microdata, RDFa) tests')


                response_status = requestHelper.response_status
                if requestHelper.response_content:
                    self.landing_url = requestHelper.redirect_url
            else:
                self.logger.warning('FsF-F2-01M :Skipping Embedded tests, no scheme/protocol detected to be able to resolve '+(str(self.id)))

        except Exception as e:
            self.logger.error('FsF-F2-01M : Resource inaccessible -: ' +str(e))
            pass
        if self.landing_url:
            if self.landing_url not in ['https://datacite.org/invalid.html']:
                if response_status == 200:
                    self.raise_warning_if_javascript_page(requestHelper.response_content)
                    up = urlparse(self.landing_url)
                    self.landing_origin = '{uri.scheme}://{uri.netloc}'.format(uri=up)
                    self.landing_html = requestHelper.getResponseContent()
                    self.landing_content_type = requestHelper.content_type
                elif response_status in [401, 402, 403]:
                    self.isMetadataAccessible = False
                    self.logger.warning(
                        'FsF-F1-02D : Resource inaccessible, identifier returned http status code -: {code}'.format(
                            code=response_status))
                else:
                    self.isMetadataAccessible = False
                    self.logger.warning(
                        'FsF-F1-02D : Resource inaccessible, identifier returned http status code -: {code}'.format(
                            code=response_status))
            else:
                self.logger.warning(
                    'FsF-F1-02D : Invalid DOI, identifier resolved to -: {code}'.format(code=self.fuji.landing_url))
                self.landing_url = None
        #we have to test landin_url again, because above it may have been set to None again.. (invalid DOI)
        if self.landing_url:
            self.set_html_typed_links()
            self.set_signposting_header_links(requestHelper.response_content, requestHelper.getResponseHeader())

            self.set_signposting_typeset_links()

            self.logger.info('FsF-F2-01M : Starting to analyse EMBEDDED metadata at -: ' + str(self.landing_url))
            #test if content is html otherwise skip embedded tests
            #print(self.landing_content_type)
            if 'html' in str(self.landing_content_type):
                # ========= retrieve schema.org (embedded, or from via content-negotiation if pid provided) =========
                extruct_metadata = self.retrieve_metadata_embedded_extruct()
                #if extruct_metadata:
                ext_meta = extruct_metadata.get('json-ld')
                self.logger.info('FsF-F2-01M : Trying to retrieve schema.org JSON-LD metadata from html page')

                schemaorg_collector = MetaDataCollectorSchemaOrg(loggerinst=self.logger,
                                                                 sourcemetadata=ext_meta,
                                                                 mapping=Mapper.SCHEMAORG_MAPPING,
                                                                 pidurl=None)
                source_schemaorg, schemaorg_dict = schemaorg_collector.parse_metadata()
                schemaorg_dict = self.exclude_null(schemaorg_dict)
                if schemaorg_dict:
                    self.namespace_uri.extend(schemaorg_collector.namespaces)
                    self.linked_namespace_uri.update(schemaorg_collector.getLinkedNamespaces())
                    self.metadata_sources.append((source_schemaorg, 'embedded'))
                    if schemaorg_dict.get('related_resources'):
                        self.related_resources.extend(schemaorg_dict.get('related_resources'))
                    #if schemaorg_dict.get('object_content_identifier'):
                    #    self.logger.info('FsF-F3-01M : Found data links in Schema.org metadata -: ' +
                    #                     str(schemaorg_dict.get('object_content_identifier')))
                    # add object type for future reference
                    self.merge_metadata(schemaorg_dict, self.landing_url, source_schemaorg, 'application/ld+json','http://schema.org', schemaorg_collector.namespaces)

                    '''
                    for i in schemaorg_dict.keys():
                        if i in self.reference_elements:
                            self.metadata_merged[i] = schemaorg_dict[i]
                            self.reference_elements.remove(i)
                    '''
                    self.logger.log(
                        self.LOG_SUCCESS,
                        'FsF-F2-01M : Found schema.org JSON-LD metadata in html page -: ' + str(schemaorg_dict.keys()))
                else:
                    self.logger.info('FsF-F2-01M : schema.org JSON-LD metadata in html page UNAVAILABLE')

                # ========= retrieve dublin core embedded in html page =========
                if self.reference_elements:
                    self.logger.info('FsF-F2-01M : Trying to retrieve Dublin Core metadata from html page')
                    dc_collector = MetaDataCollectorDublinCore(loggerinst=self.logger,
                                                               sourcemetadata=self.landing_html,
                                                               mapping=Mapper.DC_MAPPING)
                    source_dc, dc_dict = dc_collector.parse_metadata()
                    dc_dict = self.exclude_null(dc_dict)
                    if dc_dict:
                        self.namespace_uri.extend(dc_collector.namespaces)
                        #not_null_dc = [k for k, v in dc_dict.items() if v is not None]
                        self.metadata_sources.append((source_dc, 'embedded'))
                        if dc_dict.get('related_resources'):
                            self.related_resources.extend(dc_dict.get('related_resources'))
                        self.merge_metadata(dc_dict, self.landing_url, source_dc,'text/html','http://purl.org/dc/elements/1.1/', dc_collector.namespaces)

                        self.logger.log(self.LOG_SUCCESS,
                                        'FsF-F2-01M : Found DublinCore metadata -: ' + str(dc_dict.keys()))
                    else:
                        self.logger.info('FsF-F2-01M : DublinCore metadata UNAVAILABLE')
                # ========= retrieve embedded rdfa and microdata metadata ========
                self.logger.info('FsF-F2-01M : Trying to retrieve Microdata metadata from html page')

                micro_meta = extruct_metadata.get('microdata')
                microdata_collector = MetaDataCollectorMicroData(loggerinst=self.logger,
                                                                 sourcemetadata=micro_meta,
                                                                 mapping=Mapper.MICRODATA_MAPPING)
                source_micro, micro_dict = microdata_collector.parse_metadata()
                if micro_dict:
                    self.metadata_sources.append((source_micro, 'embedded'))
                    self.namespace_uri.extend(microdata_collector.getNamespaces())
                    micro_dict = self.exclude_null(micro_dict)
                    self.merge_metadata(micro_dict, self.landing_url, source_micro, 'text/html', ' http://www.w3.org/TR/microdata', microdata_collector.getNamespaces())
                    self.logger.log(self.LOG_SUCCESS,
                                    'FsF-F2-01M : Found microdata metadata -: ' + str(micro_dict.keys()))

                #================== RDFa
                self.logger.info('FsF-F2-01M : Trying to retrieve RDFa metadata from html page')
                rdfasource = MetaDataCollector.Sources.RDFA.value
                try:
                    rdflib_logger = logging.getLogger('rdflib')
                    rdflib_logger.setLevel(logging.ERROR)
                    rdfabuffer= io.StringIO(self.landing_html.decode('utf-8'))
                    rdfa_graph = pyRdfa(media_type='text/html').graph_from_source(rdfabuffer)
                    rdfa_collector = MetaDataCollectorRdf(loggerinst=self.logger,
                                                          target_url=self.landing_url, source=rdfasource)
                    rdfa_dict = rdfa_collector.get_metadata_from_graph(rdfa_graph)
                    if (len(rdfa_dict) > 0):
                        self.metadata_sources.append((rdfasource, 'embedded'))
                        self.namespace_uri.extend(rdfa_collector.getNamespaces())
                        #rdfa_dict['object_identifier']=self.pid_url
                        rdfa_dict = self.exclude_null(rdfa_dict)
                        self.merge_metadata(rdfa_dict, self.landing_url, rdfasource,'application/xhtml+xml', 'http://www.w3.org/ns/rdfa#',rdfa_collector.getNamespaces())

                        self.logger.log(self.LOG_SUCCESS,
                                        'FsF-F2-01M : Found RDFa metadata -: ' + str(rdfa_dict.keys()))
                except Exception as e:
                    #print('RDFa parsing error',e)
                    self.logger.info(
                        'FsF-F2-01M : RDFa metadata parsing exception, probably no RDFa embedded in HTML -:' + str(e))

                # ======== retrieve OpenGraph metadata
                self.logger.info('FsF-F2-01M : Trying to retrieve OpenGraph metadata from html page')

                ext_meta = extruct_metadata.get('opengraph')
                opengraph_collector = MetaDataCollectorOpenGraph(loggerinst=self.logger,
                                                                 sourcemetadata=ext_meta,
                                                                 mapping=Mapper.OG_MAPPING)
                source_opengraph, opengraph_dict = opengraph_collector.parse_metadata()
                opengraph_dict = self.exclude_null(opengraph_dict)
                if opengraph_dict:
                    self.namespace_uri.extend(opengraph_collector.namespaces)
                    self.metadata_sources.append((source_opengraph, 'embedded'))
                    self.merge_metadata(opengraph_dict, self.landing_url, source_opengraph,'text/html', 'https://ogp.me/', opengraph_collector.namespaces)

                    self.logger.log(self.LOG_SUCCESS,
                                    'FsF-F2-01M : Found OpenGraph metadata -: ' + str(opengraph_dict.keys()))
                else:
                    self.logger.info('FsF-F2-01M : OpenGraph metadata UNAVAILABLE')

                #========= retrieve signposting data links
                self.logger.info('FsF-F2-01M : Trying to identify Typed Links to data items in html page')

                data_sign_links = self.get_signposting_header_links('item')
                if data_sign_links:
                    self.logger.info('FsF-F3-01M : Found data links in response header (signposting) -: ' +
                                     str(data_sign_links))
                    if self.metadata_merged.get('object_content_identifier') is None:
                        self.metadata_merged['object_content_identifier'] = data_sign_links

                #======== retrieve OpenSearch links
                search_links = self.get_html_typed_links(rel='search')
                for search in search_links:
                    if search.get('type') in ['application/opensearchdescription+xml']:
                        self.logger.info('FsF-R1.3-01M : Found OpenSearch link in HTML head (link rel=search) -: ' +
                                         str(search['url']))
                        self.namespace_uri.append('http://a9.com/-/spec/opensearch/1.1/')

                #========= retrieve atom, GeoRSS links
                #TODO: do somethin useful with this..
                feed_links = self.get_html_typed_links(rel='alternate')
                for feed in feed_links:
                    if feed.get('type') in ['application/rss+xml']:
                        self.logger.info(
                            'FsF-R1.3-01M : Found atom/rss/georss feed link in HTML head (link rel=alternate) -: ' +
                            str(feed.get('url')))
                        feed_helper = RSSAtomMetadataProvider(self.logger, feed['url'], 'FsF-R1.3-01M')
                        feed_helper.getMetadataStandards()
                        self.namespace_uri.extend(feed_helper.getNamespaces())
                #========= retrieve typed data object links =========

                data_meta_links = self.get_html_typed_links(rel='item')
                if data_meta_links:
                    self.logger.info('FsF-F3-01M : Found data links in HTML head (link rel=item) -: ' +
                                     str(data_meta_links))
                    if self.metadata_merged.get('object_content_identifier') is None:
                        self.metadata_merged['object_content_identifier'] = data_meta_links
                # self.metadata_sources.append((MetaDataCollector.Sources.TYPED_LINK.value,'linked'))
                # signposting pid links
                signposting_header_pids = self.get_signposting_header_links('cite-as')
                signposting_html_pids = self.get_html_typed_links('cite-as')
                signposting_pids = []
                if isinstance(signposting_header_pids, list):
                    signposting_pids = signposting_header_pids
                if isinstance(signposting_html_pids, list):
                    signposting_pids.extend(signposting_html_pids)
                if signposting_pids:
                    for signpid in signposting_pids:
                        if self.metadata_merged.get('object_identifier'):
                            if isinstance(self.metadata_merged.get('object_identifier'), list):
                                if signpid not in self.metadata_merged.get('object_identifier'):
                                    self.metadata_merged['object_identifier'].append(signpid.get('url'))
                            else:
                                self.metadata_merged['object_identifier'] = [signpid.get('url')]

            else:
                self.logger.warning('FsF-F2-01M : Skipped EMBEDDED metadata identification of landing page at -: ' +
                                    str(self.landing_url) + ' expected html content but received: ' +
                                    str(self.landing_content_type))
        else:
            self.logger.warning(
                'FsF-F2-01M : Skipped EMBEDDED metadata identification, no landing page URL could be determined')
        self.check_pidtest_repeat()

    def check_pidtest_repeat(self):
        if not self.repeat_pid_check:
            self.repeat_pid_check = False
        if self.related_resources:
            for relation in self.related_resources:
                if relation.get('relation_type') == 'isPartOf':
                    parent_identifier = IdentifierHelper(relation.get('related_resource'))
                    if parent_identifier.is_persistent:
                        self.logger.info('FsF-F2-01M : Found parent (isPartOf) identifier which is a PID in metadata, you may consider to assess the parent')

        if self.metadata_merged.get('object_identifier'):
            if isinstance(self.metadata_merged.get('object_identifier'), list):
                identifiertotest = self.metadata_merged.get('object_identifier')
            else:
                identifiertotest = [self.metadata_merged.get('object_identifier')]
            if self.pid_scheme is None:
                found_pids = {}
                for pidcandidate in identifiertotest:
                    idhelper = IdentifierHelper(pidcandidate)
                    found_id_scheme = idhelper.preferred_schema
                    if idhelper.is_persistent:
                        found_pids[found_id_scheme] = idhelper.get_identifier_url()
                if len(found_pids) >= 1 and self.repeat_pid_check == False:
                    self.logger.info(
                        'FsF-F2-01M : Found object identifier in metadata, repeating PID check for FsF-F1-02D')
                    self.logger.log(
                        self.LOG_SUCCESS,
                        'FsF-F1-02D : Found object identifier in metadata during FsF-F2-01M, PID check was repeated')
                    self.repeat_pid_check = True
                    if 'doi' in found_pids:
                        self.pid_url = found_pids['doi']
                        self.pid_scheme = 'doi'
                    else:
                        self.pid_scheme, self.pid_url = next(iter(found_pids.items()))

    # Comment: not sure if we really need a separate class as proposed below. Instead we can use a dictionary
    # TODO (important) separate class to represent https://www.iana.org/assignments/link-relations/link-relations.xhtml
    # use IANA relations for extracting metadata and meaningful links
    def set_html_typed_links(self):
        try:
            self.landing_html = self.landing_html.decode()
        except (UnicodeDecodeError, AttributeError):
            pass
        if isinstance(self.landing_html, str):
            if self.landing_html:
                try:
                    dom = lxml.html.fromstring(self.landing_html.encode('utf8'))
                    links = dom.xpath('/*/head/link')
                    for l in links:
                        href = l.attrib.get('href')
                        rel = l.attrib.get('rel')
                        type = l.attrib.get('type')
                        profile = l.attrib.get('format')
                        type = str(type).strip()
                        #handle relative paths
                        linkparts = urlparse(href)
                        if linkparts.scheme == '':
                            href = urljoin(self.landing_url, href)
                        if linkparts.path.endswith('.xml'):
                            if type not in ['application/xml','text/xml'] and not type.endswith('+xml'):
                                type += '+xml'
                        #signposting links
                        #https://www.w3.org/2001/sw/RDFCore/20031212-rdfinhtml/ recommends: link rel="meta" as well as "alternate meta"
                        if rel in ['meta','alternate meta','metadata','author','collection','describes','item','type','search','alternate','describedby','cite-as','linkset','license']:
                            source = 'typed'
                            if rel in ['describedby', 'item','license','type','collection', 'linkset','cite-as']:
                                source = 'signposting'
                            self.typed_links.append({
                                'url': href,
                                'type': type,
                                'rel': rel,
                                'profile': profile,
                                'source' : source
                            })
                except:
                    self.logger.info('FsF-F2-01M : Typed links identification failed -:')
            else:
                self.logger.info('FsF-F2-01M : Expected HTML to check for typed links but received empty string ')

    def set_signposting_typeset_links(self):
        linksetlinks = []
        linksetlink ={}
        if self.get_html_typed_links('linkset'):
            linksetlinks = self.get_html_typed_links('linkset')
        elif self.get_signposting_header_links('linkset'):
            linksetlinks = self.get_signposting_header_links('linkset')
        if linksetlinks:
            linksetlink = linksetlinks[0]
        try:
            if linksetlink.get('url'):
                requestHelper = RequestHelper(linksetlink.get('url'), self.logger)
                requestHelper.setAcceptType(AcceptTypes.linkset)
                neg_source, linkset_data= requestHelper.content_negotiate('FsF-F1-02D')
                if isinstance(linkset_data, dict):
                    if isinstance(linkset_data.get('linkset'),list):
                        validlinkset = None
                        for candidatelinkset in linkset_data.get('linkset'):
                            if isinstance(candidatelinkset, dict):
                                if candidatelinkset.get('anchor') in [self.pid_url,self.landing_url]:
                                    validlinkset = candidatelinkset
                                    break
                        if validlinkset:
                            for linktype, links in validlinkset.items():
                                if linktype != 'anchor':
                                    if not isinstance(links, list):
                                        links = [links]
                                    for link in links:
                                          self.typed_links.append({
                                            'url': link.get('href'),
                                            'type': link.get('type'),
                                            'rel': linktype,
                                            'profile': link.get('profile'),
                                            'source' : 'signposting'
                                        })
                            self.logger.info('FsF-F2-01M : Found valid Signposting Linkset in provided JSON file')
                        else:
                            self.logger.warning('FsF-F2-01M : Found Signposting Linkset but none of the given anchors matches landing oage or PID')
                else:
                    validlinkset = False
                    parsed_links = self.parse_signposting_http_link_format(linkset_data.decode())
                    try:
                        if parsed_links[0].get('anchor'):
                            self.logger.info('FsF-F2-01M : Found valid Signposting Linkset in provided text file')
                            for parsed_link in parsed_links:
                                if parsed_link.get('anchor') in [self.pid_url, self.landing_url]:
                                    self.typed_links.append(parsed_link)
                                    validlinkset = True
                            if not validlinkset:
                                self.logger.warning(
                                    'FsF-F2-01M : Found Signposting Linkset but none of the given anchors matches landing oage or PID')
                    except Exception as e:
                        self.logger.warning('FsF-F2-01M : Found Signposting Linkset but could not correctly parse the file')
                        print(e)

        except Exception as e:
            self.logger.warning('FsF-F2-01M : Failed to parse Signposting Linkset -: '+str(e))


    def get_signposting_object_identifier(self):
        # check if there is a cite-as signposting link
        signposting_pid = None
        signposting_pid_link_list = self.get_signposting_header_links('cite-as')
        if signposting_pid_link_list:
            for signposting_pid_link in signposting_pid_link_list:
                signposting_pid = signposting_pid_link.get('url')
                if signposting_pid:
                    self.logger.info(
                        'FsF-F1-02D : Found object identifier (cite-as) in signposting header links -:' + str(
                            signposting_pid))
                    if not signposting_pid_link.get('type'):
                        self.logger.warning(
                            'FsF-F1-02D : Found cite-as signposting links has no type attribute-:' + str(
                                signposting_pid))
                    signidhelper = IdentifierHelper(signposting_pid)
                    found_id = signidhelper.preferred_schema
                    if signidhelper.is_persistent and self.pid_scheme is None:
                        self.pid_scheme = found_id
                        self.pid_url = signposting_pid

    def parse_signposting_http_link_format(self, signposting_link_format_text):
        found_signposting_links = []
        for preparsed_link in signposting_link_format_text.split(','):
            found_link = None
            found_type, type_match, anchor_match = None, None, None
            found_rel, rel_match = None, None
            found_formats, formats_match = None, None
            parsed_link = preparsed_link.strip().split(';')
            found_link = parsed_link[0].strip()
            for link_prop in parsed_link[1:]:
                link_prop = str(link_prop).strip()
                if link_prop.startswith('anchor'):
                    anchor_match = re.search('anchor\s*=\s*\"?([^,;"]+)\"?', link_prop)
                if link_prop.startswith('rel'):
                    rel_match = re.search('rel\s*=\s*\"?([^,;"]+)\"?', link_prop)
                elif link_prop.startswith('type'):
                    type_match = re.search('type\s*=\s*\"?([^,;"]+)\"?', link_prop)
                elif link_prop.startswith('formats'):
                    formats_match = re.search('formats\s*=\s*\"?([^,;"]+)\"?', link_prop)
            if type_match:
                found_type = type_match[1]
            if rel_match:
                found_rel = rel_match[1]
            if formats_match:
                found_formats = formats_match[1]
            signposting_link_dict = {
                'url': found_link[1:-1],
                'type': found_type,
                'rel': found_rel,
                'profile': found_formats,
                'source': 'signposting'
            }
            if anchor_match:
                signposting_link_dict['anchor'] = anchor_match[1]
            if signposting_link_dict.get('url'):
                found_signposting_links.append(signposting_link_dict)
        return  found_signposting_links

    def set_signposting_header_links(self, content, header):
        header_link_string = header.get('Link')
        if header_link_string is not None:
            self.signposting_header_links = self.parse_signposting_http_link_format(header_link_string)

            self.logger.info('FsF-F1-02D : Found signposting links in response header of landingpage -: ' + str(
                self.signposting_header_links))



    def get_html_typed_links(self, rel='item', allkeys=True):
        # Use Typed Links in HTTP Link headers to help machines find the resources that make up a publication.
        # Use links to find domains specific metadata
        datalinks = []
        if not isinstance(rel, list):
            rel = [rel]
        for typed_link in self.typed_links:
            if typed_link.get('rel') in rel:
                if not allkeys:
                    typed_link = {tlkey: typed_link[tlkey] for tlkey in ['url','type','source']}
                datalinks.append((typed_link))
        return datalinks

    def get_signposting_header_links(self, rel='item', allkeys=True):
        signlinks = []
        if not isinstance(rel, list):
            rel = [rel]
        for signposting_links in self.signposting_header_links:
            if signposting_links.get('rel') in rel:
                if not allkeys:
                    signposting_links = {slkey: signposting_links[slkey] for slkey in ['url','type','source']}
                signlinks.append(signposting_links)
        if signlinks == []:
            signlinks = None
        return signlinks

    def get_html_xml_links(self):
        xmllinks=[]
        if self.landing_html:
            try:
                soup = BeautifulSoup(self.landing_html, features="html.parser")
                links = soup.findAll('a')
                if links:
                    for link in links:
                        if link.get('href'):
                            linkparts = urlparse(link.get('href'))
                            if str(linkparts.path).endswith('.xml'):
                                xmllinks.append({'source': 'scraped', 'url':str(link.get('href')).strip(),'type': 'text/xml','rel': 'href' })
            except Exception as e:
                print('html links error: '+str(e))
                pass
        return xmllinks

    def get_guessed_xml_link(self):
        # in case object landing page URL ends with '.html' or '/html'
        # try to find out if there is some xml content if suffix is replaced by 'xml
        datalink = None
        guessed_link = None
        if self.landing_url is not None and not self.landing_url.endswith('.xml'):
            suff_res = re.search(r'.*[\.\/](html?)?$', self.landing_url)
            if suff_res is not None:
                if suff_res[1] is not None:
                    guessed_link = self.landing_url.replace(suff_res[1], 'xml')
            else:
                guessed_link = self.landing_url+'.xml'
            if guessed_link:
                try:
                    req = urllib.Request(guessed_link, method="HEAD")
                    response = urllib.urlopen(req)
                    content_type = str(response.getheader('Content-Type')).split(';')[0]
                    if content_type.strip() in ['application/xml','text/xml', 'application/rdf+xml']:
                        datalink = {
                            'source': 'guessed',
                            'url': guessed_link,
                            'type': content_type,
                            'rel': 'alternate'
                        }
                        self.logger.log(self.LOG_SUCCESS, 'FsF-F2-01M : Found XML content at -: ' + guessed_link)
                    response.close()
                except:
                    self.logger.info('FsF-F2-01M : Guessed XML retrieval failed for -: ' + guessed_link)
        return datalink

    def get_preferred_links(self, linklist):
        #prefer links which look like the landing page url
        preferred_links = []
        other_links = []
        for link in linklist:
            if self.landing_url in str(link.get('url')):
                preferred_links.append(link)
            else:
                other_links.append(link)
        return preferred_links + other_links

    def retrieve_metadata_external_rdf_negotiated(self,target_url_list=[]):
        # ========= retrieve rdf metadata namespaces by content negotiation ========
        source = MetaDataCollector.Sources.LINKED_DATA.value
        #if self.pid_scheme == 'purl':
        #    targeturl = self.pid_url
        #else:
        #    targeturl = self.landing_url

        for targeturl in target_url_list:
            self.logger.info(
                'FsF-F2-01M : Trying to retrieve RDF metadata through content negotiation from URL -: ' + str(
                    targeturl))
            neg_rdf_collector = MetaDataCollectorRdf(loggerinst=self.logger, target_url=targeturl, source=source)
            if neg_rdf_collector is not None:
                source_rdf, rdf_dict = neg_rdf_collector.parse_metadata()
                # in case F-UJi was redirected and the landing page content negotiation doesnt return anything try the origin URL
                if not rdf_dict:
                    if self.origin_url is not None and self.origin_url != targeturl:
                        neg_rdf_collector.target_url = self.origin_url
                        source_rdf, rdf_dict = neg_rdf_collector.parse_metadata()
                self.namespace_uri.extend(neg_rdf_collector.getNamespaces())
                rdf_dict = self.exclude_null(rdf_dict)
                if rdf_dict:

                    test_content_negotiation = True
                    self.logger.log(self.LOG_SUCCESS,
                                    'FsF-F2-01M : Found Linked Data metadata -: {}'.format(str(rdf_dict.keys())))
                    self.metadata_sources.append((source_rdf, 'negotiated'))
                    self.merge_metadata(rdf_dict, targeturl, source_rdf, neg_rdf_collector.getContentType(),
                                        'http://www.w3.org/1999/02/22-rdf-syntax-ns', neg_rdf_collector.getNamespaces())

                else:
                    self.logger.info('FsF-F2-01M : Linked Data metadata UNAVAILABLE')

    def retrieve_metadata_external_schemaorg_negotiated(self,target_url_list=[]):
        for target_url in target_url_list:
            # ========= retrieve json-ld/schema.org metadata namespaces by content negotiation ========
            self.logger.info(
                'FsF-F2-01M : Trying to retrieve schema.org JSON-LD metadata through content negotiation from URL -: ' + str(
                    target_url))
            schemaorg_collector = MetaDataCollectorSchemaOrg(loggerinst=self.logger,
                                                             sourcemetadata=None,
                                                             mapping=Mapper.SCHEMAORG_MAPPING,
                                                             pidurl=target_url)
            source_schemaorg, schemaorg_dict = schemaorg_collector.parse_metadata()
            schemaorg_dict = self.exclude_null(schemaorg_dict)
            if schemaorg_dict:
                self.namespace_uri.extend(schemaorg_collector.namespaces)
                self.metadata_sources.append((source_schemaorg, 'negotiated'))

                # add object type for future reference
                self.merge_metadata(schemaorg_dict, target_url, source_schemaorg, 'application/ld+json',
                                    'http://www.schema.org', schemaorg_collector.namespaces)

                self.logger.log(
                    self.LOG_SUCCESS, 'FsF-F2-01M : Found Schema.org metadata through content negotiation-: ' +
                                      str(schemaorg_dict.keys()))
            else:
                self.logger.info('FsF-F2-01M : Schema.org metadata through content negotiation UNAVAILABLE')

    def retrieve_metadata_external_xml_negotiated(self,target_url_list=[]):
        for target_url in target_url_list:
            self.logger.info(
                'FsF-F2-01M : Trying to retrieve XML metadata through content negotiation from URL -: ' + str(target_url))
            negotiated_xml_collector = MetaDataCollectorXML(loggerinst=self.logger,
                                                            target_url=self.landing_url,
                                                            link_type='negotiated')
            source_neg_xml, metadata_neg_dict = negotiated_xml_collector.parse_metadata()
            # print('### ',metadata_neg_dict)
            neg_namespace = 'unknown xml'
            metadata_neg_dict = self.exclude_null(metadata_neg_dict)
            if len(negotiated_xml_collector.getNamespaces()) > 0:
                self.namespace_uri.extend(negotiated_xml_collector.getNamespaces())
                neg_namespace = negotiated_xml_collector.getNamespaces()[0]
            self.linked_namespace_uri.update(negotiated_xml_collector.getLinkedNamespaces())
            if metadata_neg_dict:
                self.metadata_sources.append((source_neg_xml, 'negotiated'))

                self.merge_metadata(metadata_neg_dict, self.landing_url, source_neg_xml,
                                    negotiated_xml_collector.getContentType(), neg_namespace)
                ####
                self.logger.log(
                    self.LOG_SUCCESS, 'FsF-F2-01M : Found XML metadata through content negotiation-: ' +
                                      str(metadata_neg_dict.keys()))
                self.namespace_uri.extend(negotiated_xml_collector.getNamespaces())
            # also add found xml namespaces without recognized data
            elif len(negotiated_xml_collector.getNamespaces()) > 0:
                self.merge_metadata({}, self.landing_url, source_neg_xml, negotiated_xml_collector.getContentType(),
                                    neg_namespace)
    def retrieve_metadata_external_oai_ore(self):
        oai_link = self.get_html_typed_links('resourcemap')
        if oai_link:
            if oai_link.get('type') in ['application/atom+xml']:
            #elif metadata_link['type'] in ['application/atom+xml'] and metadata_link['rel'] == 'resourcemap':
                self.logger.info(
                    'FsF-F2-01M : Found e.g. Typed Links in HTML Header linking to OAI ORE (atom) Metadata -: (' +
                    str(oai_link['type'] + ')'))
                ore_atom_collector = MetaDataCollectorOreAtom(loggerinst=self.logger,
                                                              target_url=oai_link['url'])
                source_ore, ore_dict = ore_atom_collector.parse_metadata()
                ore_dict = self.exclude_null(ore_dict)
                if ore_dict:
                    self.logger.log(self.LOG_SUCCESS,
                                    'FsF-F2-01M : Found OAI ORE metadata -: {}'.format(str(ore_dict.keys())))
                    self.metadata_sources.append((source_ore, 'linked'))
                    self.merge_metadata(ore_dict, oai_link['url'], source_ore, ore_atom_collector.getContentType(),
                                        'http://www.openarchives.org/ore/terms',
                                        'http://www.openarchives.org/ore/terms')

    def retrieve_metadata_external_datacite(self):
        if self.pid_scheme:
            # ================= datacite by content negotiation ===========
            # in case use_datacite id false use the landing page URL for content negotiation, otherwise the pid url
            if self.use_datacite is True:
                datacite_target_url = self.pid_url
            else:
                datacite_target_url = self.landing_url
            dcite_collector = MetaDataCollectorDatacite(mapping=Mapper.DATACITE_JSON_MAPPING,
                                                        loggerinst=self.logger,
                                                        pid_url=datacite_target_url)
            source_dcitejsn, dcitejsn_dict = dcite_collector.parse_metadata()
            dcitejsn_dict = self.exclude_null(dcitejsn_dict)
            if dcitejsn_dict:
                test_content_negotiation = True
                # not_null_dcite = [k for k, v in dcitejsn_dict.items() if v is not None]
                self.metadata_sources.append((source_dcitejsn, 'negotiated'))
                self.logger.log(self.LOG_SUCCESS,
                                'FsF-F2-01M : Found Datacite metadata -: {}'.format(str(dcitejsn_dict.keys())))

                self.namespace_uri.extend(dcite_collector.getNamespaces())

                self.merge_metadata(dcitejsn_dict,datacite_target_url,source_dcitejsn,dcite_collector.getContentType(), 'http://datacite.org/schema',dcite_collector.getNamespaces())
            else:
                self.logger.info('FsF-F2-01M : Datacite metadata UNAVAILABLE')
        else:
            self.logger.info('FsF-F2-01M : Not a PID, therefore Datacite metadata (json) not requested.')

    def get_connected_metadata_links(self,allowedmethods = ['signposting','typed','guessed']):
        # get all links which lead to metadata are given by signposting, typed links, guessing or in html href
        connected_metadata_links = []
        signposting_header_links = []
        # signposting html links
        signposting_html_links = self.get_html_typed_links(['describedby'])
        # signposting header links
        if self.get_signposting_header_links('describedby'):
            signposting_header_links = self.get_signposting_header_links('describedby', False)
            self.logger.info(
                'FsF-F2-01M : Found metadata link as (describedby) signposting header links -:' + str(
                    signposting_header_links))
            self.metadata_sources.append((MetaDataCollector.Sources.SIGN_POSTING.value, 'signposting'))

        if signposting_header_links:
            connected_metadata_links.extend(signposting_header_links)
        if signposting_html_links:
            connected_metadata_links.extend(signposting_html_links)

        #if signposting_typeset_links:
        #    connected_metadata_links.extend(signposting_typeset_links)

        html_typed_links = self.get_html_typed_links(['meta', 'alternate meta', 'metadata','alternate'], False)
        if html_typed_links:
            connected_metadata_links.extend(html_typed_links)
        if 'guessed' in allowedmethods:
            guessed_metadata_link = self.get_guessed_xml_link()
            href_metadata_links = self.get_html_xml_links()
            if href_metadata_links:
                connected_metadata_links.extend(href_metadata_links)
            if guessed_metadata_link is not None:
                connected_metadata_links.append(guessed_metadata_link)
        return connected_metadata_links

    def retrieve_metadata_external_linked_metadata(self, allowedmethods = ['signposting', 'typed', 'guessed']):
        # follow all links identified as typed links, signposting links and get xml or rdf metadata from there
        typed_metadata_links = self.get_connected_metadata_links(allowedmethods)
        if typed_metadata_links:
            # unique entries for typed links
            typed_metadata_links = [dict(t) for t in {tuple(d.items()) for d in typed_metadata_links}]
            typed_metadata_links = self.get_preferred_links(typed_metadata_links)
            for metadata_link in typed_metadata_links:
                if not metadata_link['type']:
                    # guess type based on e.g. file suffix
                    try:
                        metadata_link['type'] = mimetypes.guess_type(metadata_link['url'])[0]
                    except Exception:
                        pass
                if re.search(r'[\/+](rdf(\+xml)?|(?:x-)?turtle|ttl|n3|n-triples|ld\+json)+$', str(metadata_link['type'])):
                    self.logger.info('FsF-F2-01M : Found e.g. Typed Links in HTML Header linking to RDF Metadata -: (' +
                                     str(metadata_link['type']) + ' ' + str(metadata_link['url']) + ')')
                    source = MetaDataCollector.Sources.RDF_TYPED_LINKS.value
                    typed_rdf_collector = MetaDataCollectorRdf(loggerinst=self.logger,
                                                               target_url=metadata_link['url'],
                                                               source=source)
                    if typed_rdf_collector is not None:
                        source_rdf, rdf_dict = typed_rdf_collector.parse_metadata()
                        self.namespace_uri.extend(typed_rdf_collector.getNamespaces())
                        rdf_dict = self.exclude_null(rdf_dict)
                        if rdf_dict:
                            test_typed_links = True
                            self.logger.log(self.LOG_SUCCESS,
                                            'FsF-F2-01M : Found Linked Data (RDF) metadata -: {}'.format(
                                                str(rdf_dict.keys())))
                            self.metadata_sources.append((source_rdf, metadata_link['source']))
                            self.merge_metadata(rdf_dict, metadata_link['url'], source_rdf,
                                                typed_rdf_collector.getContentType(),
                                                'http://www.w3.org/1999/02/22-rdf-syntax-ns',
                                                typed_rdf_collector.getNamespaces())

                        else:
                            self.logger.info('FsF-F2-01M : Linked Data metadata UNAVAILABLE')

                elif re.search(r'[+\/]xml$', str(metadata_link['type'])):
                    self.logger.info('FsF-F2-01M : Found e.g. Typed Links in HTML Header linking to XML Metadata -: (' +
                                     str(metadata_link['type'] + ' ' + metadata_link['url'] + ')'))
                    linked_xml_collector = MetaDataCollectorXML(loggerinst=self.logger,
                                                                target_url=metadata_link['url'],
                                                                link_type=metadata_link.get('source'),
                                                                pref_mime_type=metadata_link['type'])

                    if linked_xml_collector is not None:
                        source_linked_xml, linked_xml_dict = linked_xml_collector.parse_metadata()
                        lkd_namespace = 'unknown xml'
                        if len(linked_xml_collector.getNamespaces()) > 0:
                            lkd_namespace = linked_xml_collector.getNamespaces()[0]
                            self.namespace_uri.extend(linked_xml_collector.getNamespaces())
                        self.linked_namespace_uri.update(linked_xml_collector.getLinkedNamespaces())
                        if linked_xml_dict:
                            self.metadata_sources.append((MetaDataCollector.Sources.XML_TYPED_LINKS.value, metadata_link['source']))
                            self.merge_metadata(linked_xml_dict, metadata_link['url'], source_linked_xml,
                                                linked_xml_collector.getContentType(), lkd_namespace)

                            self.logger.log(self.LOG_SUCCESS,
                                'FsF-F2-01M : Found XML metadata through typed links-: ' + str(linked_xml_dict.keys()))
                        # also add found xml namespaces without recognized data
                        elif len(linked_xml_collector.getNamespaces()) > 0:
                            self.merge_metadata(dict(), metadata_link['url'], source_linked_xml,
                                                linked_xml_collector.getContentType(), lkd_namespace,
                                                linked_xml_collector.getNamespaces())
                else:
                    self.logger.info(
                        'FsF-F2-01M : Found typed link or signposting link but cannot handle given mime type -:' + str(
                            metadata_link['type']))


    def retrieve_metadata_external(self, target_url = None):

        self.logger.info(
            'FsF-F2-01M : Starting to identify EXTERNAL metadata through content negotiation or typed (signposting) links')
        if self.landing_url:
            if self.use_datacite is True:
                target_url_list = [self.pid_url, self.landing_url]
            else:
                target_url_list = [self.landing_url]
            if not target_url_list:
                target_url_list = [self.origin_url]

            if isinstance(target_url, str):
                target_url_list = [target_url]

            target_url_list = set(tu for tu in target_url_list if tu is not None)

            self.retrieve_metadata_external_xml_negotiated(target_url_list)
            self.retrieve_metadata_external_schemaorg_negotiated(target_url_list)
            self.retrieve_metadata_external_rdf_negotiated(target_url_list)
            self.retrieve_metadata_external_datacite()
            self.retrieve_metadata_external_linked_metadata(['signposting', 'linked'])
            self.retrieve_metadata_external_oai_ore()

        if self.reference_elements:
            self.logger.debug('FsF-F2-01M : Reference metadata elements NOT FOUND -: {}'.format(
                self.reference_elements))
        else:
            self.logger.debug('FsF-F2-01M : ALL reference metadata elements available')
        # Now if an identifier has been detected in the metadata, potentially check for persistent identifier has to be repeated..
        self.check_pidtest_repeat()

    def exclude_null(self, dt):
        if type(dt) is dict:
            return dict((k, self.exclude_null(v)) for k, v in dt.items() if v and self.exclude_null(v))
        elif type(dt) is list:
            try:
                return list(set([self.exclude_null(v) for v in dt if v and self.exclude_null(v)]))
            except Exception as e:
                return [self.exclude_null(v) for v in dt if v and self.exclude_null(v)]
        elif type(dt) is str:
            return dt.strip()
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
        self.get_signposting_object_identifier()
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
            soup = BeautifulSoup(response_content, features="html.parser")
            script_content = soup.findAll('script')
            for script in soup(["script", "style", "title", "noscript"]):
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
