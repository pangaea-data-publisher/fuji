import json
import logging
import os
from typing import Dict, Any
from urllib.parse import urlparse
import requests
import yaml

class Preprocessor(object):
    # static elements belong to the class.
    all_metrics_list = []
    formatted_specification = {}
    total_metrics = 0
    total_licenses = 0
    METRIC_YML_PATH = None
    SPDX_URL = None
    DATACITE_API_REPO = None
    RE3DATA_API = None
    LOV_API = None
    LOD_CLOUDNET = None
    BIOPORTAL_API = None
    BIOPORTAL_KEY = None
    all_licenses = []
    license_names = []
    metadata_standards = {}  # key=subject,value =[standards name]
    metadata_standards_uris = {} #some additional namespace uris and all uris from above as key
    science_file_formats = {}
    long_term_file_formats = {}
    open_file_formats = {}
    re3repositories: Dict[Any, Any] = {}
    linked_vocabs = {}
    default_namespaces = []
    standard_protocols = {}
    # fuji_server_dir = os.path.dirname(sys.modules['__main__'].__file__)
    fuji_server_dir = os.path.dirname(os.path.dirname(__file__))  # project_root
    header = {"Accept": "application/json"}
    logger = logging.getLogger()
    data_files_limit = 3

    @classmethod
    def retrieve_metrics_yaml(cls, yaml_metric_path, limit):
        cls.METRIC_YML_PATH = yaml_metric_path
        cls.data_files_limit = limit
        stream = open(cls.METRIC_YML_PATH, 'r')
        try:
            specification = yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            cls.logger.error(e)
        cls.all_metrics_list = specification['metrics']
        cls.total_metrics = len(cls.all_metrics_list)

        # expected output format of http://localhost:1071/uji/api/v1/metrics
        # unwanted_keys = ['question_type']
        cls.formatted_specification['total'] = cls.total_metrics
        # temp_list = []
        # for dictm in cls.all_metrics_list:
        # temp_dict = {k: v for k, v in dictm.items() if k not in unwanted_keys}
        # temp_list.append(dictm)
        # cls.formatted_specification['metrics'] = temp_list
        cls.formatted_specification['metrics'] = cls.all_metrics_list

    @classmethod
    def retrieve_datacite_re3repos(cls, re3_endpoint, datacite_endpoint, isDebugMode):
        # retrieve all client id and re3data doi from datacite
        cls.DATACITE_API_REPO = datacite_endpoint
        cls.RE3DATA_API = re3_endpoint
        re3dict_path = os.path.join(cls.fuji_server_dir, 'data', 'repodois.json')
        if isDebugMode:
            with open(re3dict_path) as f:
                cls.re3repositories = json.load(f)
        else:
            p = {'query': 're3data_id:*'}
            try:
                req = requests.get(datacite_endpoint, params=p, headers=cls.header)
                raw = req.json()
                for r in raw["data"]:
                    cls.re3repositories[r['id']] = r['attributes']['re3data']
                while 'next' in raw['links']:
                    response = requests.get(raw['links']['next']).json()
                    for r in response["data"]:
                        cls.re3repositories[r['id']] = r['attributes']['re3data']
                    raw['links'] = response['links']
                with open(re3dict_path, 'w') as f2:
                    json.dump(cls.re3repositories, f2)
            except requests.exceptions.RequestException as e:
                cls.logger.error(e)

    @classmethod
    def retrieve_licenses(cls, license_path, isDebugMode):
        data = None
        jsn_path = os.path.join(cls.fuji_server_dir, 'data', 'licenses.json')
        # The repository can be found at https://github.com/spdx/license-list-data
        # https://spdx.org/spdx-license-list/license-list-overview
        if isDebugMode:  # use local file instead of downloading the file online
            with open(jsn_path) as f:
                data = json.load(f)
        else:
            cls.SPDX_URL = license_path
            try:
                r = requests.get(cls.SPDX_URL)
                try:
                    if r.status_code == 200:
                        resp = r.json()
                        data = resp['licenses']
                        for d in data:
                            d['name'] = d['name'].lower()  # convert license name to lowercase
                        with open(jsn_path, 'w') as f:
                            json.dump(data, f)
                except json.decoder.JSONDecodeError as e1:
                    cls.logger.error(e1)
            except requests.exceptions.RequestException as e2:
                cls.logger.error(e2)
        if data:
            cls.all_licenses = data
            cls.total_licenses = len(data)
            cls.license_names = [d['name'] for d in data if 'name' in d]
            # referenceNumber = [r['referenceNumber'] for r in data if 'referenceNumber' in r]
            # seeAlso = [s['seeAlso'] for s in data if 'seeAlso' in s]
            # cls.license_urls = dict(zip(referenceNumber, seeAlso))
    @classmethod
    def retrieve_metadata_standards_uris(cls, isDebugMode):
        data = {}
        std_uri_path = os.path.join(cls.fuji_server_dir, 'data', 'metadata_standards_uris.json')
        with open(std_uri_path) as f:
            data = json.load(f)
        if data:
            cls.metadata_standards_uris  = data

    @classmethod
    def retrieve_metadata_standards(cls, catalog_url, isDebugMode):
        cls.retrieve_metadata_standards_uris(isDebugMode)
        data = {}
        std_path = os.path.join(cls.fuji_server_dir, 'data', 'metadata_standards.json')
        # The repository can be retrieved via https://rdamsc.bath.ac.uk/api/m
        # or at https://github.com/rd-alliance/metadata-catalog-dev
        if isDebugMode:  # use local file instead of downloading the file online
            with open(std_path) as f:
                data = json.load(f)
        else:
            try:
                r = requests.get(catalog_url)
                try:
                    if r.status_code == 200:
                        resp = r.json()
                        schemes = resp['metadata-schemes']
                        for s in schemes:
                            r2 = requests.get(catalog_url + str(s['id']), headers=cls.header)
                            if r2.status_code == 200:
                                std = r2.json()
                                urls = None
                                keywords = std.get('keywords')
                                standard_title = std.get('title')
                                locations = std.get('locations')
                                if locations:
                                    urls = [d['url'] for d in std.get('locations') if 'url' in d]
                                # if keywords:
                                # for k in keywords:
                                # data.setdefault(k.lower(), []).append(standard_title)
                                # else:
                                # data.setdefault('other', []).append(standard_title)
                                if standard_title:
                                    data[standard_title] = {'subject_areas': keywords, 'urls': urls}

                        with open(std_path, 'w') as f:
                            json.dump(data, f)
                except json.decoder.JSONDecodeError as e1:
                    cls.logger.error(e1)
            except requests.exceptions.RequestException as e2:
                cls.logger.error(e2)
        if data:
            cls.metadata_standards = data

    @classmethod
    def retrieve_science_file_formats(cls, isDebugMode):
        data = {}
        sci_file_path = os.path.join(cls.fuji_server_dir, 'data', 'science_formats.json')
        with open(sci_file_path) as f:
            data = json.load(f)
        if data:
            cls.science_file_formats = data

    @classmethod
    def retrieve_long_term_file_formats(cls, isDebugMode):
        data = {}
        sci_file_path = os.path.join(cls.fuji_server_dir, 'data', 'longterm_formats.json')
        with open(sci_file_path) as f:
            data = json.load(f)
        if data:
            cls.long_term_file_formats = data

    @classmethod
    def retrieve_open_file_formats(cls, isDebugMode):
        data = {}
        sci_file_path = os.path.join(cls.fuji_server_dir, 'data', 'open_formats.json')
        with open(sci_file_path) as f:
            data = json.load(f)
        if data:
            cls.open_file_formats = data

    @classmethod
    def retrieve_standard_protocols(cls, isDebugMode):
        data = {}
        protocols_path = os.path.join(cls.fuji_server_dir, 'data', 'standard_uri_protocols.json')
        with open(protocols_path) as f:
            data = json.load(f)
        if data:
            cls.standard_protocols = data

    @classmethod
    def retrieve_default_namespaces(cls):
        ns = []
        ns_file_path = os.path.join(cls.fuji_server_dir, 'data', 'default_namespaces.txt')
        with open(ns_file_path) as f:
            #ns = [line.split(':',1)[1].strip() for line in f]
            ns = [line.rstrip() for line in f]
        if ns:
            cls.default_namespaces = ns

    @classmethod
    def retrieve_linkedvocabs(cls, lov_api, lodcloud_api, isDebugMode):
    #def retrieve_linkedvocabs(cls, lov_api, lodcloud_api, bioportal_api, bioportal_key, isDebugMode):
    # may take around 20 minutes to test and import all vocabs
        cls.LOV_API = lov_api
        cls.LOD_CLOUDNET = lodcloud_api
        #cls.BIOPORTAL_API = bioportal_api
        #cls.BIOPORTAL_KEY = bioportal_key
        ld_path = os.path.join(cls.fuji_server_dir, 'data', 'linked_vocab.json')
        vocabs = []
        if isDebugMode:
            with open(ld_path) as f:
                cls.linked_vocabs = json.load(f)
        else:
            #1. retrieve records from https://lov.linkeddata.es/dataset/lov/api
            #714 vocabs, of which 104 vocabs uri specified are broken (02072020)
            try:
                req = requests.get(lov_api, headers=cls.header)
                raw_lov = req.json()
                broken = []
                cls.logger.info('{0} vocabs specified at {1}'.format(len(raw_lov), lov_api))
                for lov in raw_lov:
                    title = [i.get('value') for i in lov.get('titles') if i.get('lang') == 'en'][0]
                    uri = lov.get('uri')
                    nsp = lov.get('nsp')
                    if uri and nsp:
                      if cls.isURIActive(uri):
                          vocabs.append({'title': title, 'namespace': nsp, 'uri': uri, 'prefix': lov.get('prefix')})
                      else:
                          broken.append(uri)
                    else:
                        broken.append(uri)
                cls.logger.info('{0} vocabs uri specified are broken'.format(len(broken)))
            except requests.exceptions.RequestException as e:
                cls.logger.error(e)
            except requests.exceptions.ConnectionError as e1:
                cls.logger.error(e1)

            all_uris = [d['uri'] for d in vocabs if 'uri' in d]
            #2a. retrieve vocabs from https://lod-cloud.net/lod-data.json
            #1440 vocabs specified of which 1008 broken, so this source may be excluded in future
            try:
                r = requests.get(lodcloud_api, headers=cls.header)
                raw = r.json()
                cls.logger.info('{0} vocabs specified at {1}'.format(len(raw), lodcloud_api))
                broken_lod = []
                for r in raw:
                    d = raw.get(r)
                    website = d.get('website')
                    ns = d.get('namespace')
                    if website and ns:
                        if cls.isURIActive(website):
                            if website not in all_uris:
                                temp = {'title': d['title'], 'namespace': ns, 'uri': website, 'prefix': d.get('identifier')}
                                vocabs.append(temp)
                        else:
                            broken_lod.append(website)
                    else:
                        broken_lod.append(website)
                cls.logger.info('{0} vocabs uri specified are broken'.format(len(broken_lod)))
            except requests.exceptions.RequestException as e:
                cls.logger.error(e)
            except requests.exceptions.ConnectionError as e1:
                cls.logger.error(e1)

            #2b retrieve from BioPortal (excluded for now as the namespace in the ontology not necessarily use bioportal uri)
            # try:
            #     params = dict()
            #     params["apikey"] = bioportal_key
            #     r = requests.get(bioportal_api, params=params)
            #     onto_path = r.json()["links"]["ontologies"]
            #     resp = requests.get(onto_path, params=params)
            #     ontologies = resp.json()
            #     cls.logger.info('{0} vocabs specified at {1}'.format(len(ontologies), bioportal_api))
            #     broken_lod = []
            #     for onto in ontologies:
            #         title_onto = onto['name']
            #         prefix_onto = onto['acronym']
            #         uri_onto = onto['ui']
            # except requests.exceptions.RequestException as e:
            #     cls.logger.exception(e)
            # except requests.exceptions.ConnectionError as e1:
            #     cls.logger.exception(e1)

            #3. write to a local file
            try:
                with open(ld_path, 'w') as f:
                    json.dump(vocabs, f)
                    cls.linked_vocabs = vocabs
            except IOError as e:
                cls.logger.error("Couldn't write to file {}.".format(ld_path))

    @staticmethod
    def uri_validator(u):
        try:
            r = urlparse(u)
            return all([r.scheme, r.netloc])
        except:
            return False

    @classmethod
    def isURIActive(cls, url):
        isActive = False
        if cls.uri_validator(url):
            try:
                r = requests.head(url)
                if not (400 <= r.status_code < 600):
                    isActive = True
            except requests.exceptions.RequestException as e:
                cls.logger.error(e)
            except requests.exceptions.ConnectionError as e1:
                cls.logger.error(e1)
        return isActive

    @classmethod
    def get_licenses(cls):
        if not cls.all_licenses:
            cls.retrieve_licenses(cls.SPDX_URL, True)
        # return cls.all_licenses, cls.license_names, cls.license_urls
        return cls.all_licenses, cls.license_names

    @classmethod
    def getRE3repositories(cls):
        if not cls.re3repositories:
            cls.retrieve_datacite_re3repos(cls.RE3DATA_API, cls.DATACITE_API_REPO, True)
        return cls.re3repositories

    @classmethod
    def getLinkedVocabs(cls):
        if not cls.linked_vocabs:
            #cls.retrieve_linkedvocabs(cls.LOV_API, cls.LOD_CLOUDNET, cls.BIOPORTAL_API, cls.BIOPORTAL_KEY, True)
            cls.retrieve_linkedvocabs(cls.LOV_API, cls.LOD_CLOUDNET, True)
        return cls.linked_vocabs

    @classmethod
    def getDefaultNamespaces(cls):
        if not cls.default_namespaces:
            cls.retrieve_default_namespaces()
        return cls.default_namespaces

    @classmethod
    def get_metrics(cls):
        return cls.formatted_specification

    @classmethod
    def get_total_metrics(cls):
        return cls.total_metrics

    @classmethod
    def get_total_licenses(cls):
        return cls.total_licenses

    @classmethod
    def get_custom_metrics(cls, wanted_fields):
        new_dict = {}
        if not cls.all_metrics_list:
            cls.retrieve_metrics_yaml(cls.METRIC_YML_PATH)
        for dictm in cls.all_metrics_list:
            new_dict[dictm['metric_identifier']] = {k: v for k, v in dictm.items() if k in wanted_fields}
        return new_dict

    @classmethod
    def get_metadata_standards_uris(cls) -> object:
        if not cls.metadata_standards_uris:
            cls.retrieve_metadata_standards_uris()
        return cls.metadata_standards_uris

    @classmethod
    def get_metadata_standards(cls) -> object:
        if not cls.metadata_standards:
            cls.retrieve_metadata_standards()
        return cls.metadata_standards

    @classmethod
    def get_science_file_formats(cls) -> object:
        if not cls.science_file_formats:
            cls.retrieve_science_file_formats(True)
        return cls.science_file_formats

    @classmethod
    def get_long_term_file_formats(cls) -> object:
        if not cls.long_term_file_formats:
            cls.retrieve_long_term_file_formats(True)
        return cls.long_term_file_formats

    @classmethod
    def get_open_file_formats(cls) -> object:
        if not cls.open_file_formats:
            cls.retrieve_open_file_formats(True)
        return cls.open_file_formats

    @classmethod
    def get_standard_protocols(cls) -> object:
        if not cls.standard_protocols:
            cls.retrieve_standard_protocols(True)
        return cls.standard_protocols
