import json
import logging

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
    license_urls = {}
    re3repositories = {}

    @classmethod
    def retrieve_metrics_yaml(cls, yaml_metric_path):
        cls.METRIC_YML_PATH = yaml_metric_path
        stream = open(cls.METRIC_YML_PATH, 'r')
        try:
            specification = yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            cls.logger.exception(e)  # TODO system exit

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
    def retrieve_datacite_re3repos(cls, re3data_endpoint, datacite_endpoint):
        cls.RE3DATA_API = re3data_endpoint
        cls.DATACITE_API_REPO = datacite_endpoint
        p = {'query': 're3data_id:*'}
        header = {"content-type": "application/json"}
        try:
            req = requests.get(datacite_endpoint, params=p,headers=header) #application/json
            raw = req.json()
            for r in raw["data"]:
                cls.re3repositories[r['id']] = r['attributes']['re3data']
            while 'next' in raw['links']:
                response = requests.get(raw['links']['next']).json()
                for r in response["data"]:
                    cls.re3repositories[r['id']] = r['attributes']['re3data'] # TODO - get re3data local id
                raw['links'] = response['links']
        except requests.exceptions.RequestException as e:
            cls.logger.exception(e)

    @classmethod
    def retrieve_licenses(cls, license_path):
        # The repository can be found at https://github.com/spdx/license-list-data
        # https://spdx.org/spdx-license-list/license-list-overview
        cls.SPDX_URL = license_path
        try:
            r = requests.get(cls.SPDX_URL)
            try:
                if r.status_code == 200:
                    resp = r.json()
                    data = resp['licenses']
                    if data:
                        for d in data:  # convert license name to lowercase
                            d['name'] = d['name'].lower()
                        cls.all_licenses = data
                        cls.total_licenses = len(data)
                        cls.license_names = [d['name'] for d in data if 'name' in d]
                        referenceNumber = [r['referenceNumber'] for r in data if 'referenceNumber' in r]
                        seeAlso = [s['seeAlso'] for s in data if 'seeAlso' in s]
                        cls.license_urls = dict(zip(referenceNumber, seeAlso))
                    # v = resp['licenseListVersion'] #TODO track version number, cache json locally;  cls.all_licenses=null if download fails
                    # d = resp['releaseDate']
            except json.decoder.JSONDecodeError as e1:
                cls.logger.exception(e1)
        except requests.exceptions.RequestException as e2:  # TODO system exit
            cls.logger.exception(e2)

    @classmethod
    def get_licenses(cls):
        if not cls.all_licenses:
            cls.retrieve_licenses(cls.SPDX_URL)
        return cls.all_licenses, cls.license_names, cls.license_urls

    @classmethod
    def get_re3repositories(cls):
        if not cls.re3repositories:
            cls.retrieve_datacite_re3repos(cls.RE3DATA_API, cls.DATACITE_API_REPO)
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
