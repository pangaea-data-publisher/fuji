import json
import logging
import os
import sys
from typing import Dict, Any

import requests
import yaml

class Preprocessor(object):
    # static elements belong to the class.
    all_metrics_list = []
    formatted_specification = {}
    total_metrics = 0
    total_licenses = 0
    logger = logging.getLogger()
    METRIC_YML_PATH = None
    SPDX_URL = None
    DATACITE_API_REPO = None
    RE3DATA_API = None
    all_licenses = []
    license_names = []
    metadata_standards = {} #key=subject,value =[standards name]
    re3repositories: Dict[Any, Any] = {}
    #fuji_server_dir = os.path.dirname(sys.modules['__main__'].__file__)
    fuji_server_dir =os.path.dirname(os.path.dirname(__file__))
    header = {"Accept": "application/json"}

    @classmethod
    def retrieve_metrics_yaml(cls, yaml_metric_path):
        cls.METRIC_YML_PATH = yaml_metric_path
        stream = open(cls.METRIC_YML_PATH, 'r')
        try:
            specification = yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            cls.logger.exception(e)
        cls.all_metrics_list = specification['metrics']
        cls.total_metrics = len(cls.all_metrics_list)

        # expected output format of http://localhost:1071/uji/api/v1/metrics
        unwanted_keys = ['question_type']
        cls.formatted_specification['total'] = cls.total_metrics
        temp_list = []
        for dictm in cls.all_metrics_list:
            temp_dict = {k: v for k, v in dictm.items() if k not in unwanted_keys}
            temp_list.append(temp_dict)
        cls.formatted_specification['metrics'] = temp_list

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
                cls.logger.exception(e)

    @classmethod
    def retrieve_licenses(cls, license_path, isDebugMode):

        data = None
        jsn_path = os.path.join(cls.fuji_server_dir, 'data', 'licenses.json')
        # The repository can be found at https://github.com/spdx/license-list-data
        # https://spdx.org/spdx-license-list/license-list-overview
        if isDebugMode: # use local file instead of downloading the file online
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
                    cls.logger.exception(e1)
            except requests.exceptions.RequestException as e2:
                cls.logger.exception(e2)
        if data:
            cls.all_licenses = data
            cls.total_licenses = len(data)
            cls.license_names = [d['name'] for d in data if 'name' in d]
            # referenceNumber = [r['referenceNumber'] for r in data if 'referenceNumber' in r]
            # seeAlso = [s['seeAlso'] for s in data if 'seeAlso' in s]
            # cls.license_urls = dict(zip(referenceNumber, seeAlso))

    @classmethod
    def retrieve_metadata_standards(cls, catalog_url, isDebugMode):
        data = {}
        std_path = os.path.join(cls.fuji_server_dir, 'data', 'metadata_standards.json')
        # The repository can be found at https://github.com/spdx/license-list-data
        # https://spdx.org/spdx-license-list/license-list-overview
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
                            r2 = requests.get(catalog_url+str(s['id']), headers=cls.header)
                            if r2.status_code == 200:
                                std = r2.json()
                                keywords = std.get('keywords')
                                standard_title = std.get('title')
                                if keywords:
                                    for k in keywords:
                                        data.setdefault(k.lower(), []).append(standard_title)
                                else:
                                    data.setdefault('other', []).append(standard_title)
                        with open(std_path, 'w') as f:
                            json.dump(data, f)
                except json.decoder.JSONDecodeError as e1:
                    cls.logger.exception(e1)
            except requests.exceptions.RequestException as e2:
                cls.logger.exception(e2)
        if data:
            cls.metadata_standards = data

    @classmethod
    def get_licenses(cls):
        if not cls.all_licenses:
            cls.retrieve_licenses(cls.SPDX_URL)
        #return cls.all_licenses, cls.license_names, cls.license_urls
        return cls.all_licenses, cls.license_names

    @classmethod
    def getRE3repositories(cls):
        if not cls.re3repositories:
            cls.retrieve_datacite_re3repos(cls.RE3DATA_API, cls.DATACITE_API_REPO, True)
        return cls.re3repositories

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
    def get_metadata_standards(cls):
        return cls.metadata_standards