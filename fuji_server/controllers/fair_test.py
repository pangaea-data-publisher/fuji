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
import lxml
import rdflib
import requests
import urllib.request as urllib
from urllib.parse import urlparse
#from extruct.jsonld import JsonLdExtractor
import fuji_server.controllers.mapping as fujimap
from fuji_server.controllers.message_filter import MessageFilter
from fuji_server.controllers.preprocessor import Preprocessor
from fuji_server.models import *
from fuji_server.models import CoreMetadataOutput
import Levenshtein

class FAIRTest:

    METRICS = None
    SPDX_LICENSES = None
    SPDX_LICENSE_NAMES = None
    #SPDX_LICENSE_URLS = None
    DATACITE_REPOS = None

    def __init__(self, uid, oai=None, test_debug=False):
        self.oai_pmh = oai
        self.id = uid
        self.pid_url = None  # full pid # e.g., "https://doi.org/10.1594/pangaea.906092 or url (non-pid)
        self.landing_url = None  # url of the landing page of self.pid_url
        self.landing_html = None
        self.landing_origin = None #schema + authority of the landing page e.g. https://www.pangaea.de
        self.pid_scheme = None
        self.metadata_merged = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.isDebug = test_debug
        #self.identifier_sources = set()
        #self.license_sources = set()
        self.metadata_sources = []
        self.extruct_metadata = {}
        self.rdf_graph = None
        self.rdf_format = None
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
            #cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES, cls.SPDX_LICENSE_URLS = Preprocessor.get_licenses()
            cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES = Preprocessor.get_licenses()
        if not cls.DATACITE_REPOS:
            cls.DATACITE_REPOS = Preprocessor.get_re3repositories()

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

        # ======= CHECK IDENTIFIER UNIQUENESS =======
        found_ids = idutils.detect_identifier_schemes(self.id)  # some schemes like PMID are generic
        if len(found_ids) > 0:
            self.logger.info('FsF-F1-01D: Unique identifier schemes found {}'.format(found_ids))
            uid_output.guid = self.id
            uid_score.earned = uid_sc
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

            # ======= CHECK IDENTIFIER PERSISTENCE =======
            if found_id in fujimap.VALID_PIDS:
                self.pid_scheme = found_id
                # short_pid = id.normalize_pid(self.id, scheme=pid_scheme)
                self.pid_url = idutils.to_url(self.id, scheme=self.pid_scheme)
                self.logger.info('FsF-F1-02D: Persistence identifier scheme - {}'.format(self.pid_scheme))
            else:
                pid_score.earned = 0
                self.logger.warning('FsF-F1-02D: Not a persistent identifier scheme - {}'.format(found_id))

            # ======= RETRIEVE METADATA FROM LANDING PAGE =======
            try:
                self.logger.info('FsF-F1-02D: Retrieving page {}'.format(self.pid_url))
                r = requests.get(self.pid_url)
                self.logger.info('FsF-F1-02D: Request status code - {}'.format(r.status_code))
                if r.status_code == 200:
                    self.landing_url = r.url
                    up=urlparse(r.url)
                    self.landing_origin= '{uri.scheme}://{uri.netloc}'.format(uri=up)
                    #if re.search('text/html', r.headers['Content-Type'], re.IGNORECASE):
                    if "text/html" in r.headers["Content-Type"]:
                        self.logger.info('FsF-F1-02D: Found HTML page')
                        self.landing_html = r.text
                        #self.extruct_metadata = extruct.extract(self.landing_html.encode('utf8'))
                        self.extruct_metadata = self.parse_html(self.landing_html)
                        embedded_exists = [k for k, v in self.extruct_metadata.items() if v]
                        if embedded_exists:
                            self.logger.info('FsF-F2-01M: Formats of structured metadata embedded in HTML markup {}'.format(embedded_exists))
                        else:
                            self.logger.warning('FsF-F2-01M: No structured metadata embedded in HTML')
                    else:
                        self.logger.warning('FsF-F1-02D: HTML page NOT FOUND') #TODO Other Accept Types

                    if self.pid_scheme:
                        pid_score.earned = pid_sc # idenfier should be based on a persistence scheme and resolvable
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

        # retrieve metadata from landing page
        self.retrieve_metadata_embedded()
        return uid_result.to_dict(), pid_result.to_dict()

    def content_negotiate(self, accept_key, metric_id):
        # RDF data syntaxes (xml, n3, ntriples, trix, JSON-LD, ...)
        # Turtle is a simplified, RDF-only subset of N3.
        # N-Quads media type is application/n-quads and encoding is UTF-8.
        # N3 (Notation3) media type is text/n3, but text/rdf+n3 is also accepted. Character encoding is UTF-8.
        # JSON-LD media type is application/ld+json and the encoding is UTF-8.
        # RDF/JSON media type is application/rdf+json and the encoding is UTF-8.
        # RDF/XML media type is application/rdf+xml, but application/xml and text/xml are also accepted. The character encoding is UTF-8.
        # N-Triples media type is application/n-triples and encoding is in UTF-8.
        # Turtle media type is text/turtle, but application/x-turtle is also accepted. Character encoding is UTF-8.
        # RDFa media type is application/xhtml+xml and the encoding is UTF-8.
        # TODO handle 406 Not Acceptable or 300 Multiple Choices
        # TODO transform accept_types and parser types into a class
        accept_types = {'datacite_json': 'application/vnd.datacite.datacite+json',
                  'datacite_xml': 'application/vnd.datacite.datacite+xml',
                  'schemaorg': 'application/vnd.schemaorg.ld+json',
                  'html' :'text/html, application/xhtml+xml',
                  'json': 'application/json, text/json;q=0.5',
                  'jsonld': 'application/ld+json',
                  'rdfjson': 'application/rdf+json',
                  'ntriples': 'text/plain,application/n-triples',
                  'rdfxml': 'application/rdf+xml, text/rdf;q=0.5, application/xml;q=0.1, text/xml;q=0.1',
                  'turtle': 'text/turtle, application/turtle, application/x-turtle;q=0.6, text/n3;q=0.3, text/rdf+n3;q=0.3, application/rdf+n3;q=0.3',
                  'rdf': 'text/turtle, application/turtle, application/x-turtle;q=0.8, application/rdf+xml, text/n3;q=0.9, text/rdf+n3;q=0.9, '
                                'application/xhtml+xml;q=0.5, */*;q=0.1'}
        result = None
        if accept_key in accept_types:
            if self.pid_url is not None:
                accept_values = accept_types.get(accept_key)
                try:
                    response = requests.get(self.pid_url, headers={'Accept': accept_values})
                    self.logger.info(metric_id + ': Content negotiation accept=%s, status=%s ' % (accept_values, str(response.status_code)))
                    if response.status_code == 200:
                        content_type = response.headers["Content-Type"]
                        if content_type is not None:
                            content_type = content_type.split(";", 1)[0]
                            for k, v in accept_types.items():
                                if content_type in v:
                                    print('content_type ', content_type)
                                    if k == 'html': # TODO other types (xml)
                                        result = self.parse_html(response.text)
                                    elif k in {'schemaorg', 'json', 'jsonld','datacite_json'}:
                                        result = response.json()
                                        #result = json.loads(response.text)
                                    elif k in {'rdf','jsonld', 'rdfjson', 'ntriples', 'rdfxml','turtle'}:
                                        result = self.parse_rdf(response.text, content_type)
                                    else:
                                        result = self.parse_html(response.text) # TODO how to handle the rest e.g., text/plain
                                    break
                except requests.exceptions.RequestException as e:
                    self.logger.exception("RequestException: {}".format(e))
                    self.logger.exception("%s: , RequestException, accept = %s" % (metric_id, accept_values))
        return result

    def parse_html(self, html_texts):
        ## extract contents from the landing page using extruct, keys are 'json-ld', 'microdata', 'microformat','opengraph','rdfa'
        extracted = extruct.extract(html_texts.encode('utf8'))
        #filtered = {k: v for k, v in extracted.items() if v is not None}
        return extracted

    def parse_rdf(self, response, mime_type): #TODO (not complete!!)
        # https://rdflib.readthedocs.io/en/stable/plugin_parsers.html
        # https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.html#rdflib.graph.Graph.parse
        graph = None
        try:
            graph = rdflib.Graph()
            graph.parse(data=response, format=mime_type)
            #rdf:Description rdf:about=...
            predicate_query = graph.query("""
                                 select ?sub ?predicates ?obj
                                 where {?sub ?predicates ?obj}
                                 """)
            #for s, p, o in predicate_query:
                #print(s, p, o)
            self.rdf_format = mime_type
        except rdflib.exceptions.Error as error:
            self.logger.debug (error)
        return graph

    def retrieve_metadata_embedded(self):
        # all metadata elements required for FUJI metrics
        reference_elements = fujimap.REFERENCE_METADATA_LIST.copy()
        # TODO (IMPORTANT) simplify the conditions below
        source_schemaorg, schemaorg_dict = self.get_schemaorg_metadata()  # extract schema.org json metadata
        # retrieve schema.org (embedded, or from via content-negotiation if pid provided)
        if schemaorg_dict:
            not_null_sco = [k for k, v in schemaorg_dict.items() if v is not None]
            #self.logger.info('FsF-F2-01M: Found Schema.org metadata {} '.format(not_null_sco))
            self.metadata_sources.append(source_schemaorg)
            for i in not_null_sco:
                if i in reference_elements:
                    self.metadata_merged[i] = schemaorg_dict[i]
                    reference_elements.remove(i)
        else:
            self.logger.info('FsF-F2-01M: Schema.org metadata UNAVAILABLE')

        if reference_elements:
            if self.pid_scheme :
                # retrieve datacite json metadata based on pid
                source_dcitejsn, dcitejsn_dict = self.get_datacite_json() #TODO - different pid maybe minted from other agency than datacite
                if dcitejsn_dict:
                    not_null_dcite = [k for k, v in dcitejsn_dict.items() if v is not None]
                    #self.logger.info('FsF-F2-01M: Found Datacite metadata {} '.format(not_null_dcite))
                    self.metadata_sources.append(source_dcitejsn)
                    for r in not_null_dcite:
                        if r in reference_elements:
                            self.metadata_merged[r] = dcitejsn_dict[r]
                            reference_elements.remove(r)
                else:
                    self.logger.info('FsF-F2-01M: Datacite metadata UNAVAILABLE')
            else:
                self.logger.info('FsF-F2-01M: Not a PID, therefore Datacite metadata (json) not requested.')

        if reference_elements:
            # retrieve dublin core embedded in html page
            source_dc, dc_dict = self.get_dc_metadata()  # extract dublin core metadata
            if dc_dict:
                not_null_dc = [k for k, v in dc_dict.items() if v is not None]
                #self.logger.info('FsF-F2-01M: Found Embedded DublinCore metadata - {}'.format(not_null_dc))
                self.metadata_sources.append(source_dc)
                for d in not_null_dc:
                    if d in reference_elements:
                        self.metadata_merged[d] = dc_dict[d]
                        reference_elements.remove(d)
            else:
                self.logger.info('FsF-F2-01M: DublinCore metadata UNAVAILABLE')

        if reference_elements:
            # retrieve opengraph embedded in html page
            source_og, opengraph_dict = self.get_opengraph_metadata()  # extract opengraph metadata
            if opengraph_dict:
                not_null_og = [k for k, v in opengraph_dict.items() if v is not None]
                #self.logger.info('FsF-F2-01M: Found Embedded OpenGraph metadata {}'.format(not_null_og))
                self.metadata_sources.append(source_og)
                for m in not_null_og:
                    if m in reference_elements:
                        self.metadata_merged[m] = opengraph_dict[m]
                        reference_elements.remove(m)
            else:
                self.logger.info('FsF-F2-01M: OpenGraph metadata UNAVAILABLE')

        if self.metadata_merged.get('object_content_identifier') is None:
            self.metadata_merged ['object_content_identifier'] = self.get_html_typed_links()

        if reference_elements:
            self.logger.debug('Reference metadata elements NOT FOUND - {}'.format(reference_elements))
            # TODO (IMPORTANT!) -  try some content negotiation (rdf) + update self.self.metadata_merged
            self.rdf_graph = self.content_negotiate('rdf','FsF-F2-01M')
        else:
            self.logger.debug('ALL reference metadata elements available')

    def check_minimal_metatadata(self):
        coremeta_identifier = 'FsF-F2-01M'
        meta_sc = int(FAIRTest.METRICS.get(coremeta_identifier).get('total_score'))
        meta_score = FAIRResultCommonScore(total=meta_sc)
        coremeta_name = FAIRTest.METRICS.get(coremeta_identifier).get('metric_name')
        meta_result = CoreMetadata(id=3, metric_identifier=coremeta_identifier, metric_name=coremeta_name)

        metadata_found = {k: v for k, v in self.metadata_merged.items() if k in fujimap.REQUIRED_CORE_METADATA}
        metadata_required = fujimap.REQUIRED_CORE_METADATA
        self.logger.info('FsF-F2-01M: Required core metadata {}'.format(metadata_required))
        partial_elements = ['creator', 'title', 'object_identifier', 'publication_date']
        if set(metadata_found) == set(metadata_required):
            metadata_status = 'all metadata'
            meta_score.earned = meta_sc
            meta_passed = True
        #elif 1 <= len_found_metadata < len_metadata_required: #TODO - determine the threshold between partial and zero
        elif set(partial_elements).issubset(metadata_found):
            metadata_status = 'partial metadata'
            meta_score.earned = meta_sc - 1
            meta_passed = True
        else:
            metadata_status = 'no metadata'
            meta_score.earned = 0
            meta_passed = False

        missing = list(set(metadata_required) - set(metadata_found))
        if missing:
            self.logger.warning('FsF-F2-01M: Missing core metadata %s' %(missing))

        meta_output: CoreMetadataOutput = CoreMetadataOutput(core_metadata_status=metadata_status, core_metadata_source=self.metadata_sources)
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
        if self.extruct_metadata is not None:
            try:
                self.logger.info('FsF-F2-01M: Extract OpenGraph metadata from html page')
                # get core metadata from opengraph:
                # The Open Graph protocol enables any web page to become a rich object in a social graph
                #ext_meta = extruct.extract(self.landing_html.encode('utf8'), syntaxes=['opengraph'])
                ext_meta = self.extruct_metadata.get('opengraph')
                #if len(ext_meta['opengraph']) > 0:
                if ext_meta:
                    source = fujimap.Sources.OPENGRAPH.value
                    #if 'properties' in ext_meta['opengraph'][0]:
                    if 'properties' in ext_meta[0]:
                        #if len(ext_meta['opengraph'][0]['properties']) > 0:
                        if len(ext_meta[0]['properties']) > 0:
                            #properties = dict(ext_meta['opengraph'][0]['properties'])
                            properties = dict(ext_meta[0]['properties'])
                            for p in properties:  # p=og:image
                                if p in fujimap.OG_MAPPING.values():
                                    elem = [key for (key, value) in fujimap.OG_MAPPING.items() if value == p]
                                    elem = elem[0]
                                    open_metadata[elem] = properties[p]
            except:
                self.logger.exception('FsF-F2-01M: Failed to extract OpenGraph metadata')
        return source, open_metadata

    def get_dc_metadata(self):
        dc_core_metadata = {}
        source = None
        if self.landing_html is not None:
            try:
                self.logger.info('FsF-F2-01M: Extract DublinCore metadata from html page')
                # get core metadat from dublin core meta tags:
                # < meta name = "DCTERMS.element" content = "Value" / >
                # meta_dc_matches = re.findall('<meta\s+([^\>]*)name=\"(DC|DCTERMS)?\.([a-z]+)\"(.*?)content=\"(.*?)\"',self.landing_html)
                exp = '<\s*meta\s*([^\>]*)name\s*=\s*\"(DC|DCTERMS)?\.([A-Za-z]+)\"(.*?)content\s*=\s*\"(.*?)\"'
                meta_dc_matches = re.findall(exp, self.landing_html)
                if len(meta_dc_matches) > 0:
                    source = fujimap.Sources.DUBLINCORE.value
                    for dc_meta in meta_dc_matches:
                        # dc_meta --> ('', 'DC', 'creator', ' ', 'Hillenbrand, Claus-Dieter')
                        k = dc_meta[2]
                        v = dc_meta[4]
                        # if self.isDebug:
                        # self.logger.info('FsF-F2-01M: DublinCore metadata element, %s = %s , ' % (k, v))
                        if k in fujimap.DC_MAPPING.values():
                            elem = [key for (key, value) in fujimap.DC_MAPPING.items() if value == k][0]
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
        if self.extruct_metadata is not None:
            try:
                #ext_meta = JsonLdExtractor().extract(self.landing_html.encode('utf8'))
                ext_meta = self.extruct_metadata.get('json-ld')
                if ext_meta:
                    source = fujimap.Sources.SCHEMAORG_EMBED.value
                    ext_meta = ext_meta[0]
                else:
                    if self.pid_scheme:
                        source = fujimap.Sources.SCHEMAORG_NEGOTIATE.value
                        #TODO (IMPORTANT) PID agency may support Schema.org in JSON-LD
                        # fallback, request (doi) metadata specified in schema.org JSON-LD
                        ext_meta = self.content_negotiate('schemaorg','FsF-F2-01M')

                if ext_meta:
                    self.logger.info('FsF-F2-01M: Extract metadata from {}'.format(source))
                    # TODO filter @type": "Collection" or "@type": "Dataset"
                    # check_context_type = {"@context": "http://schema.org/","@type": "Dataset"}
                    check_context_type = {
                        "@context": ["http://schema.org/",
                                     "http://schema.org"]}  # TODO check syntax - not ending with /
                    if ext_meta['@context'] in check_context_type['@context']:
                        try:
                            jsnld_metadata = jmespath.search(fujimap.SCHEMAORG_MAPPING, ext_meta)
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
        ext_meta = self.content_negotiate('datacite_json', 'FsF-F2-01M')
        if ext_meta:
            try:
                dcite_metadata = jmespath.search(fujimap.DATACITE_JSON_MAPPING, ext_meta)
                if dcite_metadata:
                    source = fujimap.Sources.DATACITE_JSON.value
                    if dcite_metadata['creator'] is None:
                        first = dcite_metadata['creator_first']
                        last = dcite_metadata['creator_last']
                        # default type of creator is []
                        if isinstance(first, list) and isinstance(last, list):
                            if len(first) == len(last):
                                names = [i + " " + j for i, j in zip(first, last)]
                                dcite_metadata['creator'] = names

                    # convert all values (list type) into string except 'creator','license','related_resources'
                    for key, value in dcite_metadata.items():
                        if key not in ['creator','license','related_resources'] and isinstance(value, list):
                                flat = ', '.join(map(str, value))
                                dcite_metadata[key] = flat
            except Exception as e:
                self.logger.exception('Failed to extract Datacite Json - {}'.format(e.traceback.print_exc()))
        return source, dcite_metadata

    # def negotiate_datacite(self, accept_type, metric_id):
    #     accept = {'datacite_json': 'application/vnd.datacite.datacite+json',
    #               'schemaorg_jsonld': 'application/vnd.schemaorg.ld+json',
    #               'datacite_xml': 'application/vnd.datacite.datacite+xml'}
    #     result = None
    #     if accept_type in accept:
    #         if self.pid_url is not None:
    #             try:
    #                 r = requests.get(self.pid_url, headers={'Accept': accept[accept_type]})
    #                 self.logger.info(
    #                     metric_id + ': Datacite API content negotiation accept=%s, status=%s ' % (accept[accept_type], str(r.status_code)))
    #                 if r.status_code == 200:
    #                     try:
    #                         result = json.loads(r.text)
    #                     except ValueError as ve:
    #                         self.logger.debug(ve)
    #                         pass #invalid json
    #             except requests.exceptions.RequestException as e:
    #                 self.logger.exception("RequestException: {}".format(e))
    #                 self.logger.exception("FsF-F4-01M: Failed to perform %s content negotiation" % accept_type)
    #     return result

    def check_content_identifier_included(self):
        did_included_identifier = 'FsF-F3-01M'  # FsF-F3-01M: Inclusion of data identifier in metadata
        included_name = FAIRTest.METRICS.get(did_included_identifier).get('metric_name')
        did_result = IdentifierIncluded(id=4, metric_identifier=did_included_identifier, metric_name=included_name)
        did_sc = int(FAIRTest.METRICS.get(did_included_identifier).get('total_score'))
        did_score = FAIRResultCommonScore(total=did_sc)
        did_output = IdentifierIncludedOutputInner()

        id_object = self.metadata_merged.get('object_identifier')
        id_object_content = self.metadata_merged.get('object_content_identifier')
        #if id_object == self.id: http vs shttps
        self.logger.info('FsF-F3-01M: Data object identifier specified {}'.format(id_object))
        if id_object_content is not None: #TODO (IMPORTANT!) List types
            self.logger.info('FsF-F3-01M: Data object (content) identifier included {}'.format(id_object_content))
            did_output.content_identifier_included = id_object_content
            try:
                urllib.urlopen(id_object_content) # only check the status, do not download the content
            except urllib.HTTPError as e:
                self.logger.warning('FsF-F3-01M: Content identifier HTTPError code {} '.format(e.code))
            except urllib.URLError as e:
                self.logger.exception(e.reason)
            else: # will be executed if there is no exception
                did_output.content_identifier_active = True
                did_score.earned = did_sc
                did_result.passed = True
        else:
            self.logger.warning('FsF-F3-01M: Data (content) identifier is missing.')
        did_result.score = did_score
        did_result.output = did_output
        if self.isDebug:
            did_result.test_debug = self.msg_filter.getMessage(did_included_identifier)
        return did_result.to_dict()

    def get_html_typed_links(self): #TODO - item refers to data access url?
        # Use Typed Links in HTTP Link headers to help machines find the resources that make up a publication.
        # <link rel="item" href="https://doi.pangaea.de/10.1594/PANGAEA.906092?format=zip" type="application/zip"> TODO get link and type
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
        searchable_name = FAIRTest.METRICS.get(searchable_identifier).get('metric_name')
        searchable_result = Searchable(id=5, metric_identifier=searchable_identifier, metric_name=searchable_name )
        searchable_sc = int(FAIRTest.METRICS.get(searchable_identifier).get('total_score'))
        searchable_score = FAIRResultCommonScore(total=searchable_sc)
        searchable_output = SearchableOutput()
        search_mechanisms = []
        sources_registry = [fujimap.Sources.SCHEMAORG_NEGOTIATE.value, fujimap.Sources.DATACITE_JSON.value]
        # print('self.metadata_sources ', self.metadata_sources)
        search_engines_support = [fujimap.Sources.SCHEMAORG_EMBED.value, fujimap.Sources.DUBLINCORE.value]
        #r = 'Embedded Schema.org JSON-LD'
        #if r in self.metadata_sources:
        search_engine_support_match=list(set(self.metadata_sources).intersection(search_engines_support))
        if len(search_engine_support_match)>0:
            search_mechanisms.append(OutputSearchMechanisms(mechanism='structured data', mechanism_info=search_engine_support_match))
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
        licenses_list = []
        specified_licenses = self.metadata_merged.get('license')
        if specified_licenses is not None:
            if isinstance(specified_licenses, str): # licenses maybe string or list depending on metadata schemas
                specified_licenses = [specified_licenses]
            for l in specified_licenses:
                license_output = LicenseOutputInner()
                license_output.license = l
                isurl = idutils.is_url(l)
                if isurl:
                    spdx_html, spdx_osi = self.lookup_license_by_url(l)
                else: # maybe licence name
                    spdx_html, spdx_osi = self.lookup_license_by_name(l)
                if not spdx_html:
                    self.logger.warning('FsF-R1.1-01M: No SPDX license representation found')
                license_output.details_url = spdx_html
                license_output.osi_approved = spdx_osi
                licenses_list.append(license_output)
            license_result.output = licenses_list
            license_result.passed = True
            license_score.earned = license_sc
        else:
            license_score.earned = 0
            self.logger.warning('FsF-R1.1-01M: No license information is included in metadata')
        license_result.score = license_score

        if self.isDebug:
            license_result.test_debug = self.msg_filter.getMessage(license_identifier)
        return license_result.to_dict()

    def check_relatedresources(self):
        related_identifier = 'FsF-I3-01M'  # FsF-I3-01M: Meaningful links to related entities
        related_mname = FAIRTest.METRICS.get(related_identifier).get('metric_name')
        related_sc = int(FAIRTest.METRICS.get(related_identifier).get('total_score'))
        related_score = FAIRResultCommonScore(total=related_sc)
        related_result = RelatedResource(id=7, metric_identifier=related_identifier, metric_name=related_mname)
        related_output = RelatedResourceOutputInner()

        # TODO - debug message, metadata sources, extract relation and related resource identifiers, extraction string vs list (to be fixed)
        # TODO - <class 'str'> {'relationType': 'References', 'relatedIdentifier': '10.1136/bmjopen-2019-029422', 'relatedIdentifierType': 'DOI'}
        if self.metadata_merged.get('related_resources') is not None:
            related_output = self.metadata_merged['related_resources']
            related_result.passed = True
            related_result.earned = related_sc
        else:
            related_score.earned = 0
            self.logger.warning('FsF-I3-01M: No related resources specified in metadata')
        related_result.score = related_score
        related_result.output = related_output

        #if self.isDebug: # TODO
            #related_result.test_debug = self.msg_filter.getMessage(related_identifier)
        return related_result.to_dict()

    def lookup_license_by_name(self, lvalue):
        # TODO - find simpler way to run fuzzy-based search over dict/json (e.g., regex)
        html_url = None
        isOsiApproved = False
        self.logger.info('FsF-R1.1-01M: Search license SPDX details by licence name - {}'.format(lvalue))
        #Levenshtein distance similarity ratio between two license name
        sim = [Levenshtein.ratio(lvalue.lower(), i) for i in FAIRTest.SPDX_LICENSE_NAMES]
        if max(sim) > 0.85:
            index_max = max(range(len(sim)), key=sim.__getitem__)
            sim_license = FAIRTest.SPDX_LICENSE_NAMES[index_max]
            found = next((item for item in FAIRTest.SPDX_LICENSES if item['name'] == sim_license), None)
            self.logger.info('FsF-R1.1-01M: Found SPDX license representation - {}'.format(found['detailsUrl']))
            #html_url = '.html'.join(found['detailsUrl'].rsplit('.json', 1))
            html_url = found['detailsUrl'].replace(".json", ".html")
            isOsiApproved = found['isOsiApproved']
        return html_url , isOsiApproved

    def lookup_license_by_url(self, u):
        self.logger.info('FsF-R1.1-01M: Search license SPDX details by licence url - {}'.format(u))
        html_url = None
        isOsiApproved = False
        for item in FAIRTest.SPDX_LICENSES:
            #u = u.lower()
            #if any(u in v.lower() for v in item.values()):
            seeAlso = item['seeAlso']
            if any(u in v for v in seeAlso):
                self.logger.info('FsF-R1.1-01M: Found SPDX license representation - {}'.format(item['detailsUrl']))
                #html_url = '.html'.join(item['detailsUrl'].rsplit('.json', 1))
                html_url = item['detailsUrl'].replace(".json", ".html")
                isOsiApproved = item['isOsiApproved']
                break
        return html_url, isOsiApproved

    # def lookup_license_by_url_adv(self, lurl):
    #     html_url = None
    #     isOsiApproved = False
    #     self.logger.info('FsF-R1.1-01M: Extract license SPDX details by license url - {}'.format(lurl))
    #     ref_id = None
    #     max_val = 0
    #     for key, value in FAIRTest.SPDX_LICENSE_URLS.items():
    #         # Levenshtein distance similarity ratio between two license urls
    #         sim = max([Levenshtein.ratio(lurl, i) for i in value])
    #         if sim > max_val:
    #             max_val = sim
    #             ref_id = key
    #     if max_val > 0.85:
    #         found = next((item for item in FAIRTest.SPDX_LICENSES if item['referenceNumber'] == ref_id), None)
    #         self.logger.info('FsF-R1.1-01M: Found SPDX license representation - {}'.format(found['detailsUrl']))
    #         #html_url = '.html'.join(found['detailsUrl'].rsplit('.json', 1))
    #         html_url = found['detailsUrl'].replace(".json", ".html")
    #         isOsiApproved = found['isOsiApproved']
    #     else:
    #         self.logger.info('FsF-R1.1-01M: No SPDX license representation found')
    #     return html_url, isOsiApproved



    def lookup_re3data(self, re3id):
        url = Preprocessor.RE3DATA_API
        response = requests.get(url+re3id)
        #root = ElementTree.fromstring(response.content)

        html_parser = lxml.etree.HTMLParser()
        doc = lxml.etree.fromstring(response.content, parser=html_parser)
        rules = {"title": "title"}
        #p = parslepy.Parselet(rules)
        #p.extract(doc)
        #Parslepy lets you extract content from HTML and XML documents where extraction rules are defined using a JSON object or equivalent Python dict,
        # #where keys are names you want to assign to extracted content, and values are CSS selectors or XPath expressions.
        #policies
        # < r3d: metadataStandard >
        # < r3d: metadataStandardName
        # metadataStandardScheme = "DCC" > DDI - DataDocumentation itiative < / r3d: metadataStandardName >
        # < r3d: metadataStandardURL >
        # http: // www.dcc.ac.uk / resources / metadata - standards / ddi - data - documentation - initiative
        # < / r3d: metadataStandardURL >
        # < / r3d: metadataStandard >
        # <r3d: api apiType = "OAI-PMH" > http: // ws.pangaea.de / oai / < / r3d: api >
        #for node in root.iter('entry'): #r3d:metadataStandard # OAI-PMH, SPARQL, OpenDAP
            #print('\n')
            #for elem in node.iter():
                #if not elem.tag == node.tag:
                    #print("{}: {}".format(elem.tag, elem.text))
        #http://digitalcollections.uark.edu/oai/oai.php?verb=GetRecord&identifier=oai:digitalcollections.uark.edu:OzarkFolkSong/3092&metadataPrefix=oai_qdc
        #http://ws.pangaea.de/oai/provider?verb=ListMetadataFormats
        #http://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:pangaea.de:doi:10.1594/PANGAEA.66871
        #http://arXiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:cs/0112017&metadataPrefix=oai_dc
        #Sample OAI Identifier	oai:pangaea.de:doi:10.1594/PANGAEA.999999
        #Request: An identifier, in combination with a metadataPrefix, is used in the GetRecord request as a means of requesting a record in a specific metadata format from an item.
        #return None

    # def analyze_metadata_old(self):
    #     coremeta_identifier = 'FsF-F2-01M'
    #     meta_sc = int(FAIRTest.METRICS.get(coremeta_identifier).get('total_score'))
    #     meta_score = FAIRResultCommonScore(total=meta_sc)
    #     coremeta_name = FAIRTest.METRICS.get(coremeta_identifier).get('metric_name')
    #     meta_result = CoreMetadata(id=3, metric_identifier=coremeta_identifier, metric_name=coremeta_name)
    #
    #     #scrape landing page
    #     self.extruct_metadata = extruct.extract(self.landing_html.encode('utf8'))
    #     embedded_exists = [k for k, v in self.extruct_metadata.items() if v is not None] # ['json-ld', 'microdata', 'microformat','opengraph','rdfa']
    #     self.logger.info('Extracted embedded metadata from HTML markup {}'.format(embedded_exists))
    #     meta_dicts = []
    #
    #     # order should be from least importance to most importance (opegraph -> dc -> schema.org -> datacitejsn)
    #     source_og, opengraph_dict = self.get_opengraph_metadata()  # extract opengraph metadata
    #     if opengraph_dict:
    #         not_null_og = [k for k, v in opengraph_dict.items() if v is not None]
    #         self.logger.info('FsF-F2-01M: Found Embedded OpenGraph metadata {}'.format(not_null_og))
    #         if self.isDebug:
    #             if 'object_identifier' in not_null_og:
    #                 self.identifier_sources.add(source_og)
    #             if 'license' in not_null_og:
    #                 self.license_sources.add(source_og)
    #         self.metadata_sources.add(source_og)
    #         #self.metadata = opengraph_dict
    #         meta_dicts.append(opengraph_dict)
    #     else:
    #         self.logger.info('FsF-F2-01M: OpenGraph metadata UNAVAILABLE')
    #
    #     source_dc, dc_dict = self.get_dc_metadata()  # extract dublin core metadata
    #     if dc_dict:
    #         not_null_dc = [k for k, v in dc_dict.items() if v is not None]
    #         self.logger.info('FsF-F2-01M: Found Embedded DublinCore metadata - {}'.format(not_null_dc))
    #         if self.isDebug:
    #             if 'object_identifier' in not_null_dc:
    #                 self.identifier_sources.add(source_dc)
    #             if 'license' in not_null_dc:
    #                 self.license_sources.add(source_dc)
    #         self.metadata_sources.add(source_dc)
    #         #self.metadata.update(dc_dict)
    #         meta_dicts.append(dc_dict)
    #     else:
    #         self.logger.info('FsF-F2-01M: DublinCore metadata UNAVAILABLE')
    #
    #     source_schemaorg, schameorg_dict = self.get_schemaorg_metadata()  # extract schema.org json metadata
    #     if schameorg_dict:
    #         not_null_sco = [k for k,v in schameorg_dict.items() if v is not None]
    #         self.logger.info('FsF-F2-01M: Found Schema.org metadata {} '.format(not_null_sco))
    #         if self.isDebug:
    #             if 'object_identifier' in not_null_sco:
    #                 self.identifier_sources.add(source_schemaorg)
    #             if 'license' in not_null_sco:
    #                 self.license_sources.add(source_schemaorg)
    #         self.metadata_sources.add(source_schemaorg)
    #         #self.metadata.update(schameorg_dict)
    #         meta_dicts.append(schameorg_dict)
    #     else:
    #         self.logger.info('FsF-F2-01M: Schema.org metadata UNAVAILABLE')
    #
    #     if self.pid_scheme:
    #         source_dcitejsn, dcitejsn_dict = self.get_datacite_json()  # extract datacite json if pid available
    #         if dcitejsn_dict:
    #             not_null_dcite = [k for k,v in dcitejsn_dict.items() if v is not None]
    #             self.logger.info('FsF-F2-01M: Found Datacite metadata {} '.format(not_null_dcite))
    #             if self.isDebug:
    #                 if 'object_identifier' in not_null_dcite:
    #                     self.identifier_sources.add(source_dcitejsn)
    #                 if 'license' in not_null_dcite:
    #                     self.license_sources.add(source_dcitejsn)
    #             self.metadata_sources.add(source_dcitejsn)
    #             #self.metadata.update(dcitejsn_dict)
    #             meta_dicts.append(dcitejsn_dict)
    #         else:
    #             self.logger.info('FsF-F2-01M: Datacite metadata UNAVAILABLE')
    #     else:
    #         self.logger.info('FsF-F2-01M: Not a PID, no request sent to datacite metadata api.')
    #
    #     # merge all metadata dicts
    #     super_dict = collections.defaultdict(list)
    #     for d in meta_dicts:
    #         for k, v in d.items():
    #             if isinstance(d[k], list):
    #                 super_dict[k].extend(v)
    #             else:
    #                 super_dict[k].append(v)
    #             if k != 'related_resources':
    #                 super_dict[k] = list(set(super_dict[k]))
    #     self.metadata_merged = dict(super_dict)
    #     self.metadata_merged.update((k, str(v[0])) for k, v in self.metadata_merged.items() if len(v) == 1)
    #
    #     metadata_found = {k: v for k,v in self.metadata_merged.items() if k in fujimap.REQUIRED_CORE_METADATA}
    #     len_found_metadata = len([k for k,v in metadata_found.items() if v is not None])
    #     len_metadata_required = len(fujimap.REQUIRED_CORE_METADATA)
    #     metadata_status = 'no metadata'
    #     meta_passed = False
    #     if len_found_metadata == len_metadata_required:
    #         metadata_status = 'all metadata'
    #         meta_score.earned = meta_sc
    #         meta_passed = True
    #     elif 1 <= len_found_metadata < len_metadata_required:
    #         metadata_status = 'partial metadata'
    #         meta_score.earned = meta_sc - 1
    #         meta_passed = True
    #     else:
    #         meta_score.earned = 0
    #
    #     meta_output: CoreMetadataOutput = CoreMetadataOutput(core_metadata_status=metadata_status, core_metadata_source=list(self.metadata_sources))
    #     meta_output.core_metadata_found = metadata_found
    #     meta_result.passed = meta_passed
    #     meta_result.score = meta_score
    #     meta_result.output = meta_output
    #     if self.isDebug:
    #         meta_result.test_debug = self.msg_filter.getMessage(coremeta_identifier)
    #     return meta_result.to_dict()