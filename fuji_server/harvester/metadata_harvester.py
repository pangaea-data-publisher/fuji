import enum
import hashlib
import io
import json
import logging
import mimetypes
import re
import urllib
from urllib.parse import urlparse, urljoin
from tldextract import extract
import extruct
import lxml
from bs4 import BeautifulSoup
from pyRdfa import pyRdfa

from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.helper.metadata_collector import MetaDataCollector, MetadataSources, MetadataOfferingMethods
from fuji_server.helper.metadata_collector_datacite import MetaDataCollectorDatacite
from fuji_server.helper.metadata_collector_dublincore import MetaDataCollectorDublinCore
from fuji_server.helper.metadata_collector_highwire_eprints import MetaDataCollectorHighwireEprints
from fuji_server.helper.metadata_collector_microdata import MetaDataCollectorMicroData
from fuji_server.helper.metadata_collector_opengraph import MetaDataCollectorOpenGraph
from fuji_server.helper.metadata_collector_ore_atom import MetaDataCollectorOreAtom
from fuji_server.helper.metadata_collector_rdf import MetaDataCollectorRdf
from fuji_server.helper.metadata_collector_xml import MetaDataCollectorXML
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.metadata_provider_rss_atom import RSSAtomMetadataProvider
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


class MetadataHarvester():
    LOG_SUCCESS = 25
    LOG_FAILURE = 35
    signposting_relation_types = ['describedby', 'item','license','type','collection', 'author','linkset','cite-as']
    def __init__(self, uid, use_datacite = True, logger = None, auth_token = None, auth_token_type = 'Basic', allowed_harvesting_methods = None):
        uid_bytes = uid.encode('utf-8')
        self.test_id = hashlib.sha1(uid_bytes).hexdigest()
        # str(base64.urlsafe_b64encode(uid_bytes), "utf-8") # an id we can use for caching etc
        if isinstance(uid, str):
            uid = uid.strip()
        self.id = self.input_id = uid
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(self.test_id)
        self.auth_token = auth_token
        self.auth_token_type = auth_token_type
        self.landing_html = None
        self.landing_url = None
        self.landing_page_status = None
        self.landing_redirect_list =[] #urlsvisited during redirects
        self.landing_redirect_status_list = []# list with stati
        self.landing_content_type = None
        self.origin_url = None
        self.pid_url = None
        self.redirect_url = None #usually the landing page url
        self.repeat_pid_check = False
        self.related_resources = []
        self.metadata_merged = {}
        self.typed_links =[]
        self.STANDARD_PROTOCOLS = Preprocessor.get_standard_protocols()
        self.reference_elements = Mapper.REFERENCE_METADATA_LIST.value.copy()
        self.valid_pid_types = Mapper.VALID_PIDS.value
        self.namespace_uri = []
        self.metadata_sources = []
        self.metadata_unmerged = []
        self.pid_scheme = None
        self.linked_namespace_uri = {}
        self.signposting_header_links = []
        self.use_datacite = use_datacite
        self.is_html_page = False
        #Do something with this
        self.pid_collector = {}
        logging.addLevelName(self.LOG_SUCCESS, 'SUCCESS')
        logging.addLevelName(self.LOG_FAILURE, 'FAILURE')
        #set allowed methods for metadata harvesting
        self.allowed_harvesting_methods = [i for i in MetaDataCollector.getEnumMethodNames()]
        if allowed_harvesting_methods:
            if all(isinstance(x, enum.Enum) for x in allowed_harvesting_methods):
                self.allowed_harvesting_methods = allowed_harvesting_methods
        if isinstance(self.allowed_harvesting_methods,list):
            self.allowed_harvesting_sources = MetadataSources.getSourcesbyMethod(self.allowed_harvesting_methods)
        else:
            self.allowed_harvesting_sources = [i for i in MetaDataCollector.getEnumSourceNames()]
        #print('allowed sources: ', self.allowed_harvesting_sources)
        #print('allowed methods: ', self.allowed_harvesting_methods)


    def is_harvesting_source_allowed(self, method):
        #test full or part string in one of the allowed source method keys
        if method in self.allowed_harvesting_sources:
            return True
        else:
            return False

    def is_harvesting_method_allowed(self, method):
        if method in self.allowed_harvesting_methods:
            return True
        else:
            return False

    def add_metadata_source(self,source):
        self.metadata_sources.append((source.name, source.value.get('method')))

    def merge_metadata(self, metadict, url, method, format, schema='', namespaces = []):
        if not isinstance(namespaces, list):
            namespaces = [namespaces]
        if isinstance(metadict,dict):
            #self.metadata_sources.append((method_source, 'negotiated'))
            for r in metadict.keys():
                if r in self.reference_elements:
                    self.metadata_merged[r] = metadict[r]
                    self.reference_elements.pop(r)
                    #self.reference_elements.remove(r)
            if metadict.get('object_identifier'):
                if not isinstance(metadict.get('object_identifier'), list):
                    metadict['object_identifier'] = [metadict.get('object_identifier')]
                for object_identifier in metadict.get('object_identifier'):
                    resolves_to_landing_domain = False
                    pid_helper = IdentifierHelper(object_identifier, self.logger)
                    if pid_helper.identifier_url not in self.pid_collector and pid_helper.is_persistent and pid_helper.preferred_schema in self.valid_pid_types:
                        pid_record = pid_helper.get_identifier_info(self.pid_collector)
                        self.pid_collector[pid_helper.identifier_url] = pid_record
                        resolves_to_landing_domain = self.check_if_pid_resolves_to_landing_page(pid_helper.identifier_url)
                        self.pid_collector[pid_helper.identifier_url]['verified'] = resolves_to_landing_domain

            if metadict.get('related_resources'):
                self.related_resources.extend(metadict.get('related_resources'))
            if metadict.get('object_content_identifier'):
                self.logger.info('FsF-F3-01M : Found data links in '+str(format)+' metadata -: ' +
                                 str(len(metadict.get('object_content_identifier'))))
            ## add: mechanism ('content negotiation', 'typed links', 'embedded')
            ## add: format namespace
            self.metadata_unmerged.append(
                    {'method' : method,
                     'url' : url,
                     'format' : format,
                     'schema' : schema,
                     'metadata' : metadict,
                     'namespaces' : namespaces}
            )

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

    def check_if_pid_resolves_to_landing_page(self, pid_url = None):
        if pid_url in self.pid_collector:
            candidate_landing_url = self.pid_collector[pid_url].get('resolved_url')
            if candidate_landing_url and self.landing_url:
                candidate_landing_url_parts = extract(candidate_landing_url)
                landing_url_parts = extract(self.landing_url)
                input_id_domain = candidate_landing_url_parts.domain + '.' + candidate_landing_url_parts.suffix
                landing_domain = landing_url_parts.domain + '.' + landing_url_parts.suffix
                if landing_domain != input_id_domain:
                    self.logger.warning(
                        'FsF-F1-02D : Landing page domain resolved from PID found in metadata does not match with input URL domain -:'+str(pid_url)
                    )
                    self.logger.warning(
                        'FsF-F2-01M : Landing page domain resolved from PID found in metadata does not match with input URL domain -:'+str(pid_url)
                    )
                    return False
                else:
                    self.logger.info(
                        'FsF-F1-02D : Verified PID found in metadata since it is resolving to user input URL domain'
                    )
                    return True
            else:
                return False
        else:
            return False

    def check_pidtest_repeat(self):
        if not self.repeat_pid_check:
            self.repeat_pid_check = False
        if self.related_resources:
            for relation in self.related_resources:
                try:
                    if relation.get('relation_type') == 'isPartOf' and isinstance(relation.get('related_resource'), str):
                        parent_identifier = IdentifierHelper(relation.get('related_resource'), self.logger)
                        if parent_identifier.is_persistent:
                            self.logger.info('FsF-F2-01M : Found parent (isPartOf) identifier which is a PID in metadata, you may consider to assess the parent')
                except Exception as e:
                    print('Relation error: ',e)
                    pass
        if self.metadata_merged.get('object_identifier'):
            if isinstance(self.metadata_merged.get('object_identifier'), list):
                identifiertotest = self.metadata_merged.get('object_identifier')
            else:
                identifiertotest = [self.metadata_merged.get('object_identifier')]
            if self.pid_scheme is None:
                found_pids = {}
                for pidcandidate in identifiertotest:
                    idhelper = IdentifierHelper(pidcandidate, self.logger)
                    found_id_scheme = idhelper.preferred_schema
                    validated = False
                    if self.pid_collector.get(idhelper.identifier_url):
                        if self.pid_collector.get(idhelper.identifier_url).get('verified'):
                            validated = True
                    else:
                        validated = False
                    if idhelper.is_persistent and validated:
                        found_pids[found_id_scheme] = idhelper.get_identifier_url()
                if len(found_pids) >= 1 and self.repeat_pid_check == False:
                    self.logger.info(
                        'FsF-F2-01M : Found object identifier in metadata, repeating PID check for FsF-F1-02D')
                    self.logger.info(
                        'FsF-F1-02D : Found object identifier in metadata during FsF-F2-01M, therefore PID check was repeated')
                    self.repeat_pid_check = True
                    if 'doi' in found_pids:
                        self.pid_url = found_pids['doi']
                        self.pid_scheme = 'doi'
                    else:
                        self.pid_scheme, self.pid_url = next(iter(found_pids.items()))

    '''def get_html_xml_links(self):
        xmllinks=[]
        if self.landing_html:
            try:
                soup = BeautifulSoup(self.landing_html, features='html.parser')
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
                    req = urllib.Request(guessed_link, method='HEAD')
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
        return datalink'''

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
                        if rel in ['meta','alternate meta','metadata','collection','author','describes','item','type','search','alternate','describedby','cite-as','linkset','license']:
                            if rel in self.signposting_relation_types:
                                source = MetadataOfferingMethods.SIGNPOSTING
                            self.typed_links.append({
                                'url': href,
                                'type': type,
                                'rel': rel,
                                'profile': profile,
                                'source' : MetadataOfferingMethods.TYPED_LINKS
                            })
                except:
                    self.logger.info('FsF-F2-01M : Typed links identification failed -:')
            else:
                self.logger.info('FsF-F2-01M : Expected HTML to check for typed links but received empty string ')


    def set_signposting_header_links(self, content, header):
        header_link_string = header.get('Link')
        if header_link_string is not None:
            self.signposting_header_links = self.parse_signposting_http_link_format(header_link_string)
        if self.signposting_header_links:
            self.logger.info('FsF-F1-02D : Found signposting links in response header of landingpage -: ' + str(len(
                self.signposting_header_links)))

    def set_signposting_linkset_links(self):
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
                                        if linktype in self.signposting_relation_types:
                                            self.typed_links.append({
                                                'url': link.get('href'),
                                                'type': link.get('type'),
                                                'rel': linktype,
                                                'profile': link.get('profile'),
                                                'source' : MetadataOfferingMethods.SIGNPOSTING
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
        signposting_header_pids = self.get_signposting_header_links('cite-as')
        signposting_html_pids = self.get_html_typed_links('cite-as')
        signposting_pid_link_list = []
        if isinstance(signposting_header_pids, list):
            signposting_pid_link_list = signposting_header_pids
        if isinstance(signposting_html_pids, list):
            signposting_pid_link_list.extend(signposting_html_pids)

        if signposting_pid_link_list:
            for signposting_pid_link in signposting_pid_link_list:
                signposting_pid = signposting_pid_link.get('url')
                if signposting_pid:
                    self.logger.info(
                        'FsF-F1-02D : Found object identifier (cite-as) in signposting links -:' + str(
                            signposting_pid))
                    if not signposting_pid_link.get('type'):
                        self.logger.warning(
                            'FsF-F1-02D : Found cite-as signposting links has no type attribute-:' + str(
                                signposting_pid))
                    signidhelper = IdentifierHelper(signposting_pid, self.logger)
                    if self.metadata_merged.get('object_identifier'):
                        if isinstance(self.metadata_merged.get('object_identifier'), list):
                            self.metadata_merged['object_identifier'].append(signposting_pid)
                    else:
                        self.metadata_merged['object_identifier'] = [signposting_pid]
                    if signidhelper.identifier_url not in self.pid_collector and signidhelper.is_persistent and signidhelper.preferred_schema in self.valid_pid_types:
                        signpid_record = signidhelper.get_identifier_info(self.pid_collector)
                        self.pid_collector[signidhelper.identifier_url] = signpid_record


    def get_html_typed_links(self, rel='item', allkeys=True):
        # Use Typed Links in HTTP Link headers to help machines find the resources that make up a publication.
        # Use links to find domains specific metadata
        datalinks = []
        if not isinstance(rel, list):
            rel = [rel]
        for typed_link in self.typed_links:
            if typed_link.get('rel') in rel:
                if not allkeys:
                    typed_link = {tlkey: typed_link[tlkey] for tlkey in ['url', 'type', 'source']}
                datalinks.append((typed_link))
        return datalinks

    def get_signposting_header_links(self, rel='item', allkeys=True):
        signlinks = []
        if not isinstance(rel, list):
            rel = [rel]
        for signposting_links in self.signposting_header_links:
            if signposting_links.get('rel') in rel:
                if not allkeys:
                    signposting_links = {slkey: signposting_links[slkey] for slkey in ['url', 'type', 'source']}
                signlinks.append(signposting_links)
        if signlinks == []:
            signlinks = None
        return signlinks

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
                'type': str(found_type).strip(),
                'rel': str(found_rel).strip(),
                'profile': found_formats,
                'source': MetadataOfferingMethods.SIGNPOSTING
            }
            if anchor_match:
                signposting_link_dict['anchor'] = anchor_match[1]
            if signposting_link_dict.get('url') and signposting_link_dict.get('rel') in self.signposting_relation_types:
                found_signposting_links.append(signposting_link_dict)
        return  found_signposting_links

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
                self.logger.warning('FsF-F2-01M : Landing page seems to be JavaScript generated, could not detect enough content')

        except Exception as e:
            pass

    def clean_html_language_tag(self, response_content):
        # avoid RDFa errors
        try:
            langregex = r'<html\s.*lang\s*=\s*\"([^\"]+)\"'
            lm = re.search(langregex,response_content)
            if lm:
                lang = lm[1]
                if not re.match(r'^[a-zA-Z]+(?:-[a-zA-Z0-9]+)*$', lang):
                    self.logger.warning(
                        'FsF-F1-02D : Trying to fix invalid language tag detected in HTML -: '+str(lang))
                    response_content = response_content.replace(lang, 'en')
        except Exception as e:
            pass
        return response_content


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
                self.logger.info('%s : Trying to identify EMBEDDED  Microdata, OpenGraph or Schema.org -: %s' %
                                 ('FsF-F2-01M', self.landing_url))
                extracted = extruct.extract(extruct_target, syntaxes=syntaxes,encoding="utf-8")
            except Exception as e:
                extracted = {}
                self.logger.warning('%s : Failed to parse HTML embedded Microdata, OpenGraph or Schema.org -: %s' %
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
            # check if is PID in this case complete to URL and add to pid_collector
            idhelper = IdentifierHelper(self.id, self.logger)
            if idhelper.is_persistent:
                self.pid_scheme = idhelper.preferred_schema
                self.pid_url = idhelper.identifier_url
                self.pid_collector[self.pid_url] = {'pid':self.id,
                                                    'pid_url':self.pid_url,
                                                    'scheme':self.pid_scheme,
                                                    'is_persistent': True}
                #as a input PID it is verified even if it is not resolved
                self.pid_collector[self.pid_url]['verified'] = True

            input_url = idhelper.get_identifier_url()

            input_urlscheme = urlparse(input_url).scheme
            if input_urlscheme in self.STANDARD_PROTOCOLS:
                self.origin_url = input_url
                requestHelper = RequestHelper(input_url, self.logger)
                requestHelper.setAuthToken(self.auth_token,self.auth_token_type)
                #requestHelper.setAcceptType(AcceptTypes.html_xml)  # request
                requestHelper.setAcceptType(AcceptTypes.default)  # request
                neg_source, landingpage_html = requestHelper.content_negotiate('FsF-F1-02D', ignore_html=False)
                if not 'html' in str(requestHelper.content_type):
                    self.logger.info('FsF-F2-01M :Content type is ' + str(requestHelper.content_type) +
                                     ', therefore skipping Embedded metadata (microdata, RDFa) tests')
                else:
                    self.is_html_page = True
                if requestHelper.redirect_url and requestHelper.response_status == 200:

                    self.isLandingPageAccessible = True
                    self.landing_url = requestHelper.redirect_url
                    if self.pid_url in self.pid_collector:
                        self.pid_collector[self.pid_url]['verified'] = True
                        self.pid_collector[self.pid_url]['resolved_url'] = self.landing_url
                self.redirect_url = requestHelper.redirect_url
                response_status = requestHelper.response_status
                self.landing_page_status = response_status
                #if requestHelper.response_content:
                    #self.landing_url = requestHelper.redirect_url
            else:
                self.logger.warning('FsF-F2-01M :Skipping Embedded tests, no scheme/protocol detected to be able to resolve '+(str(self.id)))


        except Exception as e:
            self.logger.error('FsF-F2-01M : Resource inaccessible -: ' +str(e))
            pass
        if self.landing_url and self.is_html_page:
            if self.landing_url not in ['https://datacite.org/invalid.html']:
                if response_status == 200:
                    self.raise_warning_if_javascript_page(requestHelper.response_content)
                    up = urlparse(self.landing_url)
                    self.landing_origin = '{uri.scheme}://{uri.netloc}'.format(uri=up)
                    self.landing_html = requestHelper.getResponseContent()
                    self.landing_content_type = requestHelper.content_type
                    self.landing_redirect_list = requestHelper.redirect_list
                    self.landing_redirect_status_list = requestHelper.redirect_status_list
                elif response_status in [401, 402, 403]:
                    self.isLandingPageAccessible = False
                    self.logger.warning(
                        'FsF-F1-02D : Resource inaccessible, identifier returned http status code -: {code}'.format(
                            code=response_status))
                else:
                    self.isLandingPageAccessible = False
                    self.logger.warning(
                        'FsF-F1-02D : Resource inaccessible, identifier returned http status code -: {code}'.format(
                            code=response_status))
            else:
                self.logger.warning(
                    'FsF-F1-02D : Invalid DOI, identifier resolved to -: {code}'.format(code=self.fuji.landing_url))
                self.landing_url = None
        try:
            if requestHelper.redirect_list:
                self.landing_redirect_list = requestHelper.redirect_list
                self.landing_redirect_status_list = requestHelper.redirect_status_list
        except:
            pass
        #we have to test landin_url again, because above it may have been set to None again.. (invalid DOI)

        if self.landing_url and self.is_html_page:

            self.set_html_typed_links()
            self.set_signposting_header_links(requestHelper.response_content, requestHelper.getResponseHeader())
            self.set_signposting_linkset_links()
            if self.is_harvesting_method_allowed(MetadataOfferingMethods.HTML_EMBEDDING) or self.is_harvesting_method_allowed(MetadataOfferingMethods.MICRODATA):
                self.logger.info('FsF-F2-01M : Starting to analyse EMBEDDED metadata at -: ' + str(self.landing_url))
                #test if content is html otherwise skip embedded tests
                #print(self.landing_content_type)
                if 'html' in str(self.landing_content_type):
                    # ========= retrieve schema.org (embedded, or from via content-negotiation if pid provided) =========
                    extruct_metadata = self.retrieve_metadata_embedded_extruct()
                    #if extruct_metadata:
                    if self.is_harvesting_source_allowed(MetadataSources.SCHEMAORG_EMBEDDED):
                        ext_meta = extruct_metadata.get('json-ld')
                        self.logger.info('FsF-F2-01M : Trying to retrieve schema.org JSON-LD metadata from html page')

                        schemaorg_collector_embedded = MetaDataCollectorRdf(loggerinst=self.logger,
                                                                            json_ld_content=ext_meta,
                                                                            source = MetadataSources.SCHEMAORG_EMBEDDED)
                        source_schemaorg, schemaorg_dict = schemaorg_collector_embedded.parse_metadata()
                        schemaorg_dict = self.exclude_null(schemaorg_dict)
                        if schemaorg_dict:
                            self.namespace_uri.extend(schemaorg_collector_embedded.namespaces)
                            self.linked_namespace_uri.update(schemaorg_collector_embedded.getLinkedNamespaces())
                            #self.metadata_sources.append((source_schemaorg.name, source_schemaorg.value.get('method')))
                            self.add_metadata_source(source_schemaorg)
                            if schemaorg_dict.get('related_resources'):
                                self.related_resources.extend(schemaorg_dict.get('related_resources'))

                            # add object type for future reference
                            self.merge_metadata(schemaorg_dict, self.landing_url, source_schemaorg, 'application/ld+json','http://schema.org', schemaorg_collector_embedded.namespaces)
                            self.logger.log(
                                self.LOG_SUCCESS,
                                'FsF-F2-01M : Found schema.org JSON-LD metadata in html page -: ' + str(schemaorg_dict.keys()))
                        else:
                            self.logger.info('FsF-F2-01M : schema.org JSON-LD metadata in html page UNAVAILABLE')
                    else:
                        self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(MetadataSources.SCHEMAORG_EMBEDDED.value.get('label')))
                    # ========= retrieve highwire and eprints embedded in html page =========
                    if self.reference_elements:
                        if self.is_harvesting_source_allowed(MetadataSources.HIGHWIRE_EPRINTS_EMBEDDED):
                            self.logger.info('FsF-F2-01M : Trying to retrieve Highwire and eprints metadata from html page')
                            hw_collector = MetaDataCollectorHighwireEprints(loggerinst=self.logger,
                                                                       sourcemetadata=self.landing_html)
                            source_hw, hw_dict = hw_collector.parse_metadata()
                            hw_dict = self.exclude_null(hw_dict)
                            if hw_dict:
                                self.namespace_uri.extend(hw_collector.namespaces)
                                #not_null_dc = [k for k, v in dc_dict.items() if v is not None]
                                self.add_metadata_source(source_hw)
                                #self.metadata_sources.append((source_hw, 'embedded'))
                                if hw_dict.get('related_resources'):
                                    self.related_resources.extend(hw_dict.get('related_resources'))
                                self.merge_metadata(hw_dict, self.landing_url, source_hw,'text/html','highwire_eprints', hw_collector.namespaces)

                                self.logger.log(self.LOG_SUCCESS,
                                                'FsF-F2-01M : Found Highwire or eprints metadata -: ' + str(hw_dict.keys()))
                            else:
                                self.logger.info('FsF-F2-01M : Highwire or eprints metadata UNAVAILABLE')
                        else:
                            self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                                MetadataSources.HIGHWIRE_EPRINTS_EMBEDDED.value.get('label')))

                    # ========= retrieve dublin core embedded in html page =========
                    if self.reference_elements:
                        if self.is_harvesting_source_allowed(MetadataSources.DUBLINCORE_EMBEDDED):
                            self.logger.info('FsF-F2-01M : Trying to retrieve Dublin Core metadata from html page')
                            dc_collector = MetaDataCollectorDublinCore(loggerinst=self.logger,
                                                                       sourcemetadata=self.landing_html,
                                                                       mapping=Mapper.DC_MAPPING)
                            source_dc, dc_dict = dc_collector.parse_metadata()
                            dc_dict = self.exclude_null(dc_dict)
                            if dc_dict:
                                self.namespace_uri.extend(dc_collector.namespaces)
                                #not_null_dc = [k for k, v in dc_dict.items() if v is not None]
                                #self.metadata_sources.append((source_dc, 'embedded'))
                                self.add_metadata_source(source_dc)
                                if dc_dict.get('related_resources'):
                                    self.related_resources.extend(dc_dict.get('related_resources'))
                                self.merge_metadata(dc_dict, self.landing_url, source_dc,'text/html','http://purl.org/dc/elements/1.1/', dc_collector.namespaces)

                                self.logger.log(self.LOG_SUCCESS,
                                                'FsF-F2-01M : Found DublinCore metadata -: ' + str(dc_dict.keys()))
                            else:
                                self.logger.info('FsF-F2-01M : DublinCore metadata UNAVAILABLE')
                        else:
                            self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                                MetadataSources.DUBLINCORE_EMBEDDED.value.get('label')))
                    # ========= retrieve embedded rdfa and microdata metadata ========

                    if self.is_harvesting_source_allowed(MetadataSources.MICRODATA_EMBEDDED):
                        self.logger.info('FsF-F2-01M : Trying to retrieve Microdata metadata from html page')

                        micro_meta = extruct_metadata.get('microdata')
                        microdata_collector = MetaDataCollectorMicroData(loggerinst=self.logger,
                                                                         sourcemetadata=micro_meta,
                                                                         mapping=Mapper.MICRODATA_MAPPING)
                        source_micro, micro_dict = microdata_collector.parse_metadata()
                        if micro_dict:
                            #self.metadata_sources.append((source_micro, 'embedded'))
                            self.add_metadata_source(source_micro)
                            self.namespace_uri.extend(microdata_collector.getNamespaces())
                            micro_dict = self.exclude_null(micro_dict)
                            self.merge_metadata(micro_dict, self.landing_url, source_micro, 'text/html', 'http://www.w3.org/TR/microdata', microdata_collector.getNamespaces())
                            self.logger.log(self.LOG_SUCCESS,
                                            'FsF-F2-01M : Found microdata metadata -: ' + str(micro_dict.keys()))
                    else:
                        self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                            MetadataSources.MICRODATA_EMBEDDED.value.get('label')))

                    #================== RDFa
                    if self.is_harvesting_source_allowed(MetadataSources.RDFA_EMBEDDED):
                        self.logger.info('FsF-F2-01M : Trying to retrieve RDFa metadata from html page')
                        rdfasource = MetadataSources.RDFA_EMBEDDED
                        try:
                            rdfa_dict = {}
                            rdflib_logger = logging.getLogger('rdflib')
                            rdflib_logger.setLevel(logging.ERROR)
                            try:
                                rdfa_html = self.landing_html.decode('utf-8')
                            except Exception as e:
                                rdfa_html = self.landing_html
                                pass
                            rdfa_html = self.clean_html_language_tag(rdfa_html)
                            rdfabuffer= io.StringIO(rdfa_html)
                            # rdflib is no longer supporting RDFa: https://stackoverflow.com/questions/68500028/parsing-htmlrdfa-in-rdflib
                            # https://github.com/RDFLib/rdflib/discussions/1582

                            rdfa_graph = pyRdfa(media_type='text/html').graph_from_source(rdfabuffer)

                            rdfa_collector = MetaDataCollectorRdf(loggerinst=self.logger,
                                                                  target_url=self.landing_url,
                                                                  source=rdfasource)
                            try:
                                rdfa_dict = rdfa_collector.get_metadata_from_graph(rdfa_graph)
                            except Exception as e:
                                print('RDFa Graph error: ',e)
                            if (len(rdfa_dict) > 0):
                                #self.metadata_sources.append((rdfasource, 'embedded'))
                                self.add_metadata_source(rdfasource)
                                self.namespace_uri.extend(rdfa_collector.getNamespaces())
                                #rdfa_dict['object_identifier']=self.pid_url
                                rdfa_dict = self.exclude_null(rdfa_dict)
                                self.merge_metadata(rdfa_dict, self.landing_url, rdfasource,'application/xhtml+xml', 'http://www.w3.org/ns/rdfa#',rdfa_collector.getNamespaces())

                                self.logger.log(self.LOG_SUCCESS,
                                                'FsF-F2-01M : Found RDFa metadata -: ' + str(rdfa_dict.keys()))
                        except Exception as e:
                            print('RDFa parsing error',str(e))
                            self.logger.info(
                                'FsF-F2-01M : RDFa metadata parsing exception, probably no RDFa embedded in HTML -:' + str(e))
                    else:
                        self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                            MetadataSources.RDFA_EMBEDDED.value.get('label')))

                    # ======== retrieve OpenGraph metadata
                    if self.is_harvesting_source_allowed(MetadataSources.OPENGRAPH_EMBEDDED):

                        self.logger.info('FsF-F2-01M : Trying to retrieve OpenGraph metadata from html page')

                        ext_meta = extruct_metadata.get('opengraph')
                        opengraph_collector = MetaDataCollectorOpenGraph(loggerinst=self.logger,
                                                                         sourcemetadata=ext_meta,
                                                                         mapping=Mapper.OG_MAPPING)
                        source_opengraph, opengraph_dict = opengraph_collector.parse_metadata()
                        opengraph_dict = self.exclude_null(opengraph_dict)
                        if opengraph_dict:
                            self.namespace_uri.extend(opengraph_collector.namespaces)
                            #self.metadata_sources.append((source_opengraph, 'embedded'))
                            self.add_metadata_source(source_opengraph)
                            self.merge_metadata(opengraph_dict, self.landing_url, source_opengraph,'text/html', 'https://ogp.me/', opengraph_collector.namespaces)

                            self.logger.log(self.LOG_SUCCESS,
                                            'FsF-F2-01M : Found OpenGraph metadata -: ' + str(opengraph_dict.keys()))
                        else:
                            self.logger.info('FsF-F2-01M : OpenGraph metadata UNAVAILABLE')
                    else:
                        self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                            MetadataSources.OPENGRAPH_EMBEDDED.value.get('label')))
                else:
                    self.logger.warning('FsF-F2-01M : Skipped EMBEDDED metadata identification of landing page at -: ' +
                                        str(self.landing_url) + ' expected html content but received: ' +
                                        str(self.landing_content_type))
            else:
                self.logger.warning(
                    'FsF-F2-01M :Skipping Embedded tests, since no EMBEDDED method in allowed harvesting methods: ' + (
                        str(self.allowed_harvesting_sources)))

                ############## end of embedded metadata content harvesting


            if self.is_harvesting_method_allowed(MetadataOfferingMethods.TYPED_LINKS) or self.is_harvesting_method_allowed(MetadataOfferingMethods.SIGNPOSTING):
                # ========= retrieve signposting data links
                self.logger.info('FsF-F2-01M : Trying to identify Typed Links to data items in html page')

                data_sign_links = self.get_signposting_header_links('item')
                if data_sign_links:
                    self.logger.info('FsF-F3-01M : Found data links in response header (signposting) -: ' +
                                     str(len(data_sign_links)))
                    if self.metadata_merged.get('object_content_identifier') is None:
                        self.metadata_merged['object_content_identifier'] = data_sign_links
                # ========= retrieve signposting or typed data object links =========
                data_meta_links = self.get_html_typed_links(rel='item')
                if data_meta_links:
                    self.logger.info('FsF-F3-01M : Found data links in HTML head (link rel=item) -: ' +
                                     str(len(data_meta_links)))
                    if self.metadata_merged.get('object_content_identifier') is None:
                        self.metadata_merged['object_content_identifier'] = data_meta_links
                # self.metadata_sources.append((MetaDataCollector.Sources.TYPED_LINK.value,'linked'))
            else:
                self.logger.warning(
                    'FsF-F2-01M :Skipping typed or signposting link collection')

            #======== retrieve OpenSearch links
            search_links = self.get_html_typed_links(rel='search')
            for search in search_links:
                if search.get('type') in ['application/opensearchdescription+xml']:
                    self.logger.info('FsF-R1.3-01M : Found OpenSearch link in HTML head (link rel=search) -: ' +
                                     str(search['url']))
                    self.namespace_uri.append('http://a9.com/-/spec/opensearch/1.1/')

        else:
            self.logger.warning(
                'FsF-F2-01M : Skipped EMBEDDED metadata identification, no landing page URL or HTML content could be determined')
        self.check_pidtest_repeat()


    def retrieve_metadata_external_rdf_negotiated(self,target_url_list=[]):
        # ========= retrieve rdf metadata namespaces by content negotiation ========
        if self.is_harvesting_source_allowed(MetadataSources.RDF_NEGOTIATED):
            source = MetadataSources.RDF_NEGOTIATED
            #if self.pid_scheme == 'purl':
            #    targeturl = self.pid_url
            #else:
            #    targeturl = self.landing_url

            for targeturl in target_url_list:
                self.logger.info(
                    'FsF-F2-01M : Trying to retrieve RDF metadata through content negotiation from URL -: ' + str(
                        targeturl))
                neg_rdf_collector = MetaDataCollectorRdf(loggerinst=self.logger, target_url=targeturl, source=source)
                neg_rdf_collector.set_auth_token(self.auth_token, self.auth_token_type)
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
                        #self.metadata_sources.append((source_rdf, 'negotiated'))
                        self.add_metadata_source(source_rdf)
                        self.merge_metadata(rdf_dict, targeturl, source_rdf, neg_rdf_collector.getContentType(),
                                            'http://www.w3.org/1999/02/22-rdf-syntax-ns', neg_rdf_collector.getNamespaces())

                    else:
                        self.logger.info('FsF-F2-01M : Linked Data metadata UNAVAILABLE')
        else:
            self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                MetadataSources.RDF_NEGOTIATED.value.get('label')))

    def retrieve_metadata_external_schemaorg_negotiated(self,target_url_list=[]):
        if self.is_harvesting_source_allowed(MetadataSources.SCHEMAORG_NEGOTIATED):
            for target_url in target_url_list:
                # ========= retrieve json-ld/schema.org metadata namespaces by content negotiation ========
                self.logger.info(
                    'FsF-F2-01M : Trying to retrieve schema.org JSON-LD metadata through content negotiation from URL -: ' + str(
                        target_url))
                schemaorg_collector_negotiated = MetaDataCollectorRdf(loggerinst=self.logger,
                                                                      target_url=target_url,
                                                                      source = MetadataSources.SCHEMAORG_NEGOTIATED)
                schemaorg_collector_negotiated.setAcceptType(AcceptTypes.jsonld)
                source_schemaorg, schemaorg_dict = schemaorg_collector_negotiated.parse_metadata()
                schemaorg_dict = self.exclude_null(schemaorg_dict)
                if schemaorg_dict:
                    self.namespace_uri.extend(schemaorg_collector_negotiated.namespaces)
                    #self.metadata_sources.append((source_schemaorg, 'negotiated'))
                    self.add_metadata_source(source_schemaorg)

                    # add object type for future reference
                    self.merge_metadata(schemaorg_dict, target_url, source_schemaorg, 'application/ld+json',
                                        'http://www.schema.org', schemaorg_collector_negotiated.namespaces)

                    self.logger.log(
                        self.LOG_SUCCESS, 'FsF-F2-01M : Found Schema.org metadata through content negotiation-: ' +
                                          str(schemaorg_dict.keys()))
                else:
                    self.logger.info('FsF-F2-01M : Schema.org metadata through content negotiation UNAVAILABLE')
        else:
            self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                MetadataSources.SCHEMAORG_NEGOTIATED.value.get('label')))

    def retrieve_metadata_external_xml_negotiated(self,target_url_list=[]):
        if self.is_harvesting_source_allowed(MetadataSources.XML_NEGOTIATED):
            for target_url in target_url_list:
                self.logger.info(
                    'FsF-F2-01M : Trying to retrieve XML metadata through content negotiation from URL -: ' + str(target_url))
                negotiated_xml_collector = MetaDataCollectorXML(loggerinst=self.logger,
                                                                target_url=self.landing_url,
                                                                link_type=MetadataOfferingMethods.CONTENT_NEGOTIATION)
                negotiated_xml_collector.set_auth_token(self.auth_token,self.auth_token_type)
                source_neg_xml, metadata_neg_dict = negotiated_xml_collector.parse_metadata()
                # print('### ',metadata_neg_dict)
                neg_namespace = 'unknown xml'
                metadata_neg_dict = self.exclude_null(metadata_neg_dict)
                if len(negotiated_xml_collector.getNamespaces()) > 0:
                    self.namespace_uri.extend(negotiated_xml_collector.getNamespaces())
                    neg_namespace = negotiated_xml_collector.getNamespaces()[0]
                self.linked_namespace_uri.update(negotiated_xml_collector.getLinkedNamespaces())
                #print('LINKED NS XML ',self.linked_namespace_uri)
                if metadata_neg_dict:
                    #self.metadata_sources.append((source_neg_xml, 'negotiated'))
                    self.add_metadata_source(source_neg_xml)
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
        else:
            self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                MetadataSources.XML_NEGOTIATED.value.get('label')))
    '''
    def retrieve_metadata_external_georss(self):
        # ========= retrieve atom, GeoRSS links
        feed_links = self.get_html_typed_links(rel='alternate')
        for feed in feed_links:
            if feed.get('type') in ['application/rss+xml']:
                self.logger.info(
                    'FsF-R1.3-01M : Found atom/rss/georss feed link in HTML head (link rel=alternate) -: ' +
                    str(feed.get('url')))
                #feed_helper = RSSAtomMetadataProvider(self.logger, feed['url'], 'FsF-R1.3-01M')
                #feed_helper.getMetadataStandards()
                #self.namespace_uri.extend(feed_helper.getNamespaces())
    '''
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
                    self.add_metadata_source(source_ore)
                    self.merge_metadata(ore_dict, oai_link['url'], source_ore, ore_atom_collector.getContentType(),
                                        'http://www.openarchives.org/ore/terms',
                                        'http://www.openarchives.org/ore/terms')

    def retrieve_metadata_external_datacite(self):
        if self.is_harvesting_source_allowed(MetadataSources.DATACITE_JSON_NEGOTIATED):
            #if self.pid_scheme:
            # ================= datacite by content negotiation ===========
            # in case use_datacite id false use the landing page URL for content negotiation, otherwise the pid url
            if self.use_datacite is True and self.pid_url:
                datacite_target_url = self.pid_url
            else:
                datacite_target_url = self.landing_url
            if datacite_target_url:
                dcite_collector = MetaDataCollectorDatacite(mapping=Mapper.DATACITE_JSON_MAPPING,
                                                            loggerinst=self.logger,
                                                            pid_url=datacite_target_url)
                source_dcitejsn, dcitejsn_dict = dcite_collector.parse_metadata()
                dcitejsn_dict = self.exclude_null(dcitejsn_dict)
                if dcitejsn_dict:
                    #self.metadata_sources.append((source_dcitejsn, 'negotiated'))
                    self.add_metadata_source(source_dcitejsn)
                    self.logger.log(self.LOG_SUCCESS,
                                    'FsF-F2-01M : Found Datacite metadata -: {}'.format(str(dcitejsn_dict.keys())))

                    self.namespace_uri.extend(dcite_collector.getNamespaces())

                    self.merge_metadata(dcitejsn_dict,datacite_target_url,source_dcitejsn,dcite_collector.getContentType(), 'http://datacite.org/schema',dcite_collector.getNamespaces())
                else:
                    self.logger.info('FsF-F2-01M : Datacite metadata UNAVAILABLE')
            else:
                self.logger.info('FsF-F2-01M : No target URL (PID or landing page) given, therefore Datacite metadata (json) not requested.')
        else:
            self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                MetadataSources.DATACITE_JSON_NEGOTIATED.value.get('label')))

    def get_connected_metadata_links(self):
        # get all links which lead to metadata are given by signposting, typed links, guessing or in html href
        if MetadataOfferingMethods.SIGNPOSTING in self.allowed_harvesting_methods or MetadataOfferingMethods.TYPED_LINKS in self.allowed_harvesting_methods:
            connected_metadata_links = []
            signposting_header_links = []
            # signposting html links
            signposting_html_links = self.get_html_typed_links(['describedby'])
            # signposting header links
            if MetadataOfferingMethods.SIGNPOSTING in self.allowed_harvesting_methods:
                if self.get_signposting_header_links('describedby'):
                    signposting_header_links = self.get_signposting_header_links('describedby', False)
                    self.logger.info(
                        'FsF-F2-01M : Found metadata link as (describedby) signposting header links -:' + str(
                            [sl.get('url') for sl in signposting_header_links]))
                if signposting_header_links:
                    connected_metadata_links.extend(signposting_header_links)
            if signposting_html_links:
                connected_metadata_links.extend(signposting_html_links)
            #if signposting_typeset_links:
            #    connected_metadata_links.extend(signposting_typeset_links)
            if MetadataOfferingMethods.TYPED_LINKS in self.allowed_harvesting_methods:
                html_typed_links = self.get_html_typed_links(['meta', 'alternate meta', 'metadata','alternate'], False)
                if html_typed_links:
                    connected_metadata_links.extend(html_typed_links)
            '''if 'guessed' in allowedmethods:
                guessed_metadata_link = self.get_guessed_xml_link()
                href_metadata_links = self.get_html_xml_links()
                if href_metadata_links:
                    connected_metadata_links.extend(href_metadata_links)
                if guessed_metadata_link is not None:
                    connected_metadata_links.append(guessed_metadata_link)'''
        return connected_metadata_links

    def retrieve_metadata_external_linked_metadata(self):
        # follow all links identified as typed links, signposting links and get xml or rdf metadata from there
        typed_metadata_links = self.get_connected_metadata_links()
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
                    if self.is_harvesting_source_allowed(MetadataSources.RDF_TYPED_LINKS) or self.is_harvesting_source_allowed(MetadataSources.RDF_SIGNPOSTING_LINKS):
                        self.logger.info('FsF-F2-01M : Found e.g. Typed Links in HTML Header linking to RDF Metadata -: (' +
                                         str(metadata_link['type']) + ' ' + str(metadata_link['url']) + ')')
                        if metadata_link.get('source') == MetadataOfferingMethods.SIGNPOSTING:
                            source = MetadataSources.RDF_SIGNPOSTING_LINKS
                        else:
                            source = MetadataSources.RDF_TYPED_LINKS
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
                                #self.metadata_sources.append((source_rdf, metadata_link['source']))
                                self.add_metadata_source(source_rdf)
                                self.merge_metadata(rdf_dict, metadata_link['url'], source_rdf,
                                                    typed_rdf_collector.getContentType(),
                                                    'http://www.w3.org/1999/02/22-rdf-syntax-ns',
                                                    typed_rdf_collector.getNamespaces())

                            else:
                                self.logger.info('FsF-F2-01M : Linked Data metadata UNAVAILABLE')
                    else:
                        self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                            MetadataSources.RDF_TYPED_LINKS.value.get('label')))

                elif re.search(r'[+\/]xml$', str(metadata_link['type'])):
                    if self.is_harvesting_source_allowed(MetadataSources.XML_TYPED_LINKS) or self.is_harvesting_source_allowed(MetadataSources.XML_SIGNPOSTING_LINKS):
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
                                #self.metadata_sources.append((MetaDataCollector.Sources.XML_TYPED_LINKS.value.get('label'), metadata_link['source']))
                                if metadata_link.get('source') == MetadataOfferingMethods.SIGNPOSTING:
                                    self.add_metadata_source(MetadataSources.XML_SIGNPOSTING_LINKS)
                                else:
                                    self.add_metadata_source(MetadataSources.XML_TYPED_LINKS)
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
                        self.logger.info('FsF-F2-01M : Skipped disabled harvesting method -: ' + str(
                            MetadataSources.XML_TYPED_LINKS.value.get('label')))
                else:
                    self.logger.info(
                        'FsF-F2-01M : Found typed link or signposting link but will ignore (can\'t handle) mime type -:' + str(
                            metadata_link['type']))


    def retrieve_metadata_external(self, target_url = None, repeat_mode = False):
        if self.is_harvesting_method_allowed(MetadataOfferingMethods.CONTENT_NEGOTIATION) or self.is_harvesting_method_allowed(MetadataOfferingMethods.TYPED_LINKS) or self.is_harvesting_method_allowed(MetadataOfferingMethods.SIGNPOSTING):
            self.logger.info(
                'FsF-F2-01M : Starting to identify EXTERNAL metadata through content negotiation or typed (signposting) links')
            if self.landing_url or self.pid_url:
                if not self.landing_url:
                    self.logger.warning(
                        'FsF-F2-01M : Landing page could not be identified, therefore EXTERNAL metadata is based on PID only and may be incomplete')
                target_url_list = [self.origin_url, self.pid_url, self.landing_url]
                if self.use_datacite is False and 'doi' == self.pid_scheme:
                    if self.origin_url == self.pid_url:
                        target_url_list = [self.landing_url]
                    else:
                        target_url_list = [self.origin_url,self.landing_url]
                #specific target url
                if isinstance(target_url, str):
                    target_url_list = [target_url]

                target_url_list = set(tu for tu in target_url_list if tu is not None)
                self.retrieve_metadata_external_xml_negotiated(target_url_list)
                self.retrieve_metadata_external_schemaorg_negotiated(target_url_list)
                self.retrieve_metadata_external_rdf_negotiated(target_url_list)
                self.retrieve_metadata_external_datacite()
                if not repeat_mode:
                    self.retrieve_metadata_external_linked_metadata()
                    self.retrieve_metadata_external_oai_ore()


            if self.reference_elements:
                self.logger.debug('FsF-F2-01M : Reference metadata elements NOT FOUND -: {}'.format(
                    self.reference_elements))
            else:
                self.logger.debug('FsF-F2-01M : ALL reference metadata elements available')
            # Now if an identifier has been detected in the metadata, potentially check for persistent identifier has to be repeated..
            self.check_pidtest_repeat()
        else:
            self.logger.warning(
                'FsF-F2-01M : Skipped EXTERNAL metadata identification, no landing page URL or HTML content could be determined')


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
    
