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
    URN_RESOLVER = {'urn:doi:': 'https://dx.doi.org/',
                    'urn:lex:br':'https://www.lexml.gov.br/',
                    'urn:nbn:de':'https://nbn-resolving.org/',
                    'urn:nbn:se':'https://urn.kb.se/resolve?urn=',
                    'urn:nbn:at':'https://resolver.obvsg.at/',
                    'urn:nbn:hr':'https://urn.nsk.hr/',
                    'urn:nbn:no':'https://urn.nb.no/',
                    'urn:nbn:fi':'https://urn.fi/',
                    'urn:nbn:it':'https://nbn.depositolegale.it/',
                    'urn:nbn:nl':'https://www.persistent-identifier.nl/'}

    def __init__(self, idstring):
        self.identifier = idstring
        self.normalized_id = self.identifier
        if self.identifier and isinstance(self.identifier, str):
            if len(self.identifier) > 4 and not self.identifier.isnumeric():
                #workaround to identify nbn urns given together with standard resolver urls:
                if 'urn:' in self.identifier:
                    try:
                        urnsplit = self.identifier.split(r'(urn:(?:nbn|doi|lex|):[a-z]+)',re.IGNORECASE)
                        if len(urnsplit) > 1:
                            urnid = urnsplit[1]
                            candidateurn = urnid+str(urnsplit[2])
                            candresolver = re.sub(r'https?://','',urnsplit[0])
                            if candresolver in self.URN_RESOLVER.values():
                                self.resolver = candresolver
                                self.identifier = candidateurn
                    except Exception as e:
                        print('URN split error',e)
                   #workaround to resolve lsids:
                #idutils.LANDING_URLS['lsid'] ='http://www.lsid.info/resolver/?lsid={pid}'
                #workaround to recognize https purls and arks
                if 'https://purl.' in self.identifier or '/ark:' in self.identifier:
                    self.identifier = self.identifier.replace('https:', 'http:')
                #workaround to identify arks properly:
                self.identifier = self.identifier.replace('/ark:' , '/ark:/' )
                self.identifier = self.identifier.replace('/ark://', '/ark:/')
                generic_identifiers_org_pattern = '^([a-z0-9\._]+):(.+)'
                # idutils check
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
                                    self.identifier_schemes.remove('url')
                            self.preferred_schema = self.identifier_schemes[0]
                            self.normalized_id = idutils.normalize_pid(self.identifier, self.preferred_schema)
                        self.identifier_url = idutils.to_url(self.identifier, self.preferred_schema)
                if self.preferred_schema in Mapper.VALID_PIDS.value or self.preferred_schema in self.IDENTIFIERS_ORG_DATA.keys(
                ):
                    self.is_persistent = True

    def get_preferred_schema(self):
        return self.preferred_schema

    def get_identifier_schemes(self):
        return self.identifier_schemes

    def get_identifier_url(self):
        return self.identifier_url

    def get_normalized_id(self):
        return self.normalized_id
