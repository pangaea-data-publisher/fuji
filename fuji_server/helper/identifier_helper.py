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
import urllib

import idutils
import re

from fuji_server.helper.metadata_mapper import Mapper

from fuji_server.helper.preprocessor import Preprocessor


class IdentifierHelper:
    IDENTIFIERS_ORG_DATA = Preprocessor.get_identifiers_org_data()
    identifier_schemes = []
    preferred_schema = None  # the preferred schema
    identifier_url = None
    identifier = None
    method = 'idutils'
    resolver = None
    is_persistent = False
    URN_RESOLVER = {'urn:doi:': 'dx.doi.org/',
                    'urn:lex:br':'www.lexml.gov.br/',
                    'urn:nbn:de':'nbn-resolving.org/',
                    'urn:nbn:se':'urn.kb.se/resolve?urn=',
                    'urn:nbn:at':'resolver.obvsg.at/',
                    'urn:nbn:hr':'urn.nsk.hr/',
                    'urn:nbn:no':'urn.nb.no/',
                    'urn:nbn:fi':'urn.fi/',
                    'urn:nbn:it':'nbn.depositolegale.it/',
                    'urn:nbn:nl':'www.persistent-identifier.nl/'}

    #check if the urn is a urn plus resolver URL
    def check_resolver_urn(self, idstring):
        ret = False
        if 'urn:' in idstring and not idstring.startswith('urn:'):
            try:
                urnsplit = re.split(r'(urn:(?:nbn|doi|lex|):[a-z]+)', idstring, re.IGNORECASE)
                if len(urnsplit) > 1:
                    urnid = urnsplit[1]
                    candidateurn = urnid + str(urnsplit[2])
                    candresolver = re.sub(r'https?://', '', urnsplit[0])
                    if candresolver in self.URN_RESOLVER.values():
                        if idutils.is_urn(candidateurn):
                            self.identifier_schemes = ['url', 'urn']
                            self.preferred_schema = 'urn'
                            self.normalized_id = candidateurn
                            self.identifier_url = 'https://' + candresolver + candidateurn
                            ret = True
            except Exception as e:
                print('URN parsing error', e)
        return ret

    def __init__(self, idstring):
        self.identifier = idstring
        self.normalized_id = self.identifier
        if self.identifier and isinstance(self.identifier, str):
            idparts = urllib.parse.urlparse(self.identifier)
            if len(self.identifier) > 4 and not self.identifier.isnumeric():
                #workaround to identify nbn urns given together with standard resolver urls:
                self.check_resolver_urn(self.identifier)
                 #workaround to resolve lsids:
                #idutils.LANDING_URLS['lsid'] ='http://www.lsid.info/resolver/?lsid={pid}'
                #workaround to recognize https purls and arks
                if '/purl.archive.org/' in self.identifier:
                    self.identifier = self.identifier.replace('/purl.archive.org/', '/purl.org/')
                if 'https://purl.' in self.identifier or '/ark:' in self.identifier:
                    self.identifier = self.identifier.replace('https:', 'http:')
                #workaround to identify arks properly:
                self.identifier = self.identifier.replace('/ark:' , '/ark:/' )
                self.identifier = self.identifier.replace('/ark://', '/ark:/')
                generic_identifiers_org_pattern = '^([a-z0-9\._]+):(.+)'
                #w3id check
                if not self.identifier_schemes:
                    if idparts.scheme == 'https' and idparts.netloc in ['w3id.org','www.w3id.org'] and idparts.path != '':
                        self.identifier_schemes = ['w3id','url']
                        self.preferred_schema = 'w3id'
                        self.identifier_url = self.identifier
                        self.normalized_id =self.identifier
                # idutils check
                if not self.identifier_schemes:
                    self.identifier_schemes = idutils.detect_identifier_schemes(self.identifier)

                # identifiers.org check
                if not self.identifier_schemes:
                    self.method = 'identifiers.org'
                    idmatch = re.search(generic_identifiers_org_pattern, self.identifier)
                    if idmatch:
                        found_prefix = idmatch[1]
                        found_suffix = idmatch[2]
                        if found_prefix in self.IDENTIFIERS_ORG_DATA.keys():
                            if (re.search(self.IDENTIFIERS_ORG_DATA[found_prefix]['pattern'], found_suffix)):
                                self.identifier_schemes = [found_prefix, 'identifiers_org']
                                self.preferred_schema = found_prefix
                            self.identifier_url = str(self.IDENTIFIERS_ORG_DATA[found_prefix]['url_pattern']).replace(
                                '{$id}', found_suffix)
                            self.normalized_id = found_prefix.lower() + ':' + found_suffix
                else:
                    # preferred schema
                    if self.identifier_schemes:
                        if len(self.identifier_schemes) > 0:
                            if len(self.identifier_schemes) > 1:
                                if 'url' in self.identifier_schemes:  # ['doi', 'url']
                                    #move url to end of list
                                    self.identifier_schemes.append(self.identifier_schemes.pop(self.identifier_schemes.index('url')))
                                    #self.identifier_schemes.remove('url')
                            self.preferred_schema = self.identifier_schemes[0]
                            if not self.normalized_id:
                                self.normalized_id = idutils.normalize_pid(self.identifier, self.preferred_schema)
                            if not self.identifier_url:
                                self.identifier_url = self.to_url(self.identifier, self.preferred_schema)
                            #print('IDURL ',self.identifier_url, self.preferred_schema)
                if self.preferred_schema in Mapper.VALID_PIDS.value or self.preferred_schema in self.IDENTIFIERS_ORG_DATA.keys(
                ):
                    self.is_persistent = True

    def to_url(self, id, schema):
        idurl = None
        try:
            if schema == 'ark':
                idurl = id
            else:
                idurl = idutils.to_url(id, schema)
            if schema in ['doi', 'handle']:
                idurl = idurl.replace('http:', 'https:')
        except Exception as e:
            print('ID helper to_url error '+str(e))
        return idurl

    def get_preferred_schema(self):
        return self.preferred_schema

    def get_identifier_schemes(self):
        return self.identifier_schemes

    def get_identifier_url(self):
        return self.identifier_url

    def get_normalized_id(self):
        return self.normalized_id
