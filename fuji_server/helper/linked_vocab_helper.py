import json
from tldextract import extract
from urllib.parse import urlparse
import re
import requests
import os


class linked_vocab_helper:
    fuji_server_dir = os.path.dirname(os.path.dirname(__file__))  # project_root

    def __init__(self, linked_vocab_index={}):
        self.linked_vocab_index = linked_vocab_index
        self.linked_vocab_dict = {}
        self.ignore_prefixes = ['orcid','doi','isni','ror','wikipedia']
        #prefixes used for identifiers only not terms
        self.ignore_domain = ['orcid.org', 'doi.org','ror.org','zenodo.org']

    def set_linked_vocab_dict(self):
        print('Setting up the vocab dict.........................')
        # a new implementation based on bioportal etc..

        for ont_reg_file in os.listdir(os.path.join(self.fuji_server_dir, 'data', 'linked_vocabs')):
            if ont_reg_file.endswith('.json'): #and ont_reg_file not in ['fuji_ontologies.json', 'bioregistry.json']:
                with open(os.path.join(self.fuji_server_dir, 'data', 'linked_vocabs', ont_reg_file),
                          encoding='utf-8') as reg_file:
                    reg_ontologies = json.load(reg_file)
                    self.linked_vocab_dict.update(reg_ontologies)

    def split_iri(self, iri):
        ret = {}
        domainparts = extract(iri)
        if domainparts.suffix:
            ret['domain'] = domainparts.domain + '.' + domainparts.suffix
            if domainparts.domain:
                if domainparts.subdomain:
                    ret['subdomain'] = domainparts.subdomain
                else:
                    ret['subdomain'] = 'www'
        else:
            ret['domain'], ret['subdomain'] = None, None

        ret['iri'] = iri
        if domainparts.domain and domainparts.suffix:
            ret['path'] = iri.split(domainparts.domain + '.' + domainparts.suffix)[1]
        else:
            ret['path'] = None
        return ret

    def add_linked_vocab_index_entry(self, prefix, reg_entry):
        prefix = reg_entry.get('prefix')
        uri_regex = reg_entry.get('pattern')
        uri_format = reg_entry.get('uri_format')
        namespace = uri_format.split('$1')[0]
        subjects = reg_entry.get('subjects')
        title = reg_entry.get('name')
        uriparts = self.split_iri(uri_format)
        if uriparts.get('domain') not in self.ignore_domain:
            if not self.linked_vocab_index.get(uriparts.get('domain')):
                self.linked_vocab_index[uriparts.get('domain')] = {}
            if not self.linked_vocab_index[uriparts.get('domain')].get(uriparts.get('subdomain')):
                self.linked_vocab_index[uriparts.get('domain')][uriparts.get('subdomain')] = [
                    {'prefix': prefix, 'pattern': uriparts.get('path'), 'regex': uri_regex, 'subjects': subjects,
                     'name': title,'namespace':namespace}]
            else:
                self.linked_vocab_index[uriparts.get('domain')][uriparts.get('subdomain')].append(
                    {'prefix': prefix, 'pattern': uriparts.get('path'), 'regex': uri_regex, 'subjects': subjects,
                     'name': title,'namespace':namespace})

    def set_linked_vocab_index(self):
        if not self.linked_vocab_dict:
            self.set_linked_vocab_dict()
        for rk, rd in self.linked_vocab_dict.items():
            if str(rd.get('prefix')).lower() not in self.ignore_prefixes:
                if isinstance(rd, dict):
                    if rd.get('uri_format'):
                        self.add_linked_vocab_index_entry(rk, rd)
                    for k, d in rd.items():
                        if isinstance(d, dict):
                            if d.get('uri_format'):
                                if not d.get('name'):
                                    # try to get the first name in dict
                                    try:
                                        for el in (*rd.values(),):
                                            if el.get('name'):
                                                d['name'] = el.get('name')
                                                break
                                    except:
                                        pass
                                self.add_linked_vocab_index_entry(rk, d)

    def get_overlap(self, s1, s2):
        result = ''
        for char in s1:
            if char in s2 and not char in result:
                result += char
        return len(result)


    def get_linked_vocab_by_iri(self, IRI, isnamespaceIRI=False, firstonly = True):
        IRI = IRI.strip()
        if isnamespaceIRI:
            IRI = IRI.rstrip('/#')
        iri_parts = self.split_iri(IRI)
        onto_match = []
        final_onto_match = None
        tested_patterns = []
        iri_domain = iri_parts.get('domain')
        if self.linked_vocab_index.get(iri_domain):
            if self.linked_vocab_index[iri_domain].get(iri_parts.get('subdomain')):
                for reg_res in self.linked_vocab_index[iri_domain][iri_parts.get('subdomain')]:
                    # full match
                    if reg_res.get('namespace') == IRI:
                        onto_match.append({'score': len(iri_parts.get('path')), 'match': reg_res})
                    else:
                        # print(reg_res.get('pattern').replace('$1',''), iri_parts.get('path'))
                        if reg_res.get('pattern'):
                            pattern_check = False
                            if isnamespaceIRI:
                                #print(reg_res.get('pattern').split('$1')[0].rstrip('/#') , iri_parts.get('path').rstrip('/#'))
                                if reg_res.get('pattern').split('$1')[0].rstrip('/#') in iri_parts.get('path').rstrip('/#'):
                                    pattern_check = True
                            else:
                                if reg_res.get('pattern').split('$1')[0] in iri_parts.get('path'):
                                    pattern_check = True
                            if pattern_check:
                                if reg_res.get('regex'):
                                    comb_regex = reg_res.get('regex').lstrip('^').rstrip('$')
                                else:
                                    if '?' in reg_res.get('pattern'):
                                        reg_res['pattern']=reg_res.get('pattern').replace('?',r'\?')
                                    comb_regex = reg_res.get('pattern').split('$1')[0].rstrip('/#')

                                if comb_regex not in tested_patterns:
                                    tested_patterns.append(comb_regex)
                                    comb_match = re.search(comb_regex, iri_parts.get('path'))
                                    score = self.get_overlap(iri_parts.get('path'), reg_res.get('pattern').split('$1')[0])
                                if comb_match:
                                    #if len(comb_match.groups()) > 0:
                                    #    if comb_match[1]:
                                    #        print('++++++',comb_match[1],reg_res.get('namespace'))
                                    #        reg_res['namespace'] = IRI.split(comb_match[1])[0] + comb_match[1]
                                    onto_match.append({'score': score, 'match': reg_res})
            maxscore = 0
            if onto_match:
                for ont_m in onto_match:
                    if ont_m['score'] >= maxscore:
                        final_onto_match = ont_m['match']

        return final_onto_match
