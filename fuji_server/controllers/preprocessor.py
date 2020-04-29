import logging
import json
import requests
import yaml
import logging

class Preprocessor(object):

    # static elements belong to the class.
    all_metrics_list = []
    formatted_specification = {}
    total_metrics = 0
    total_licenses = 0
    logger = logging.getLogger()

    @classmethod
    def retrieve_metrics_yaml(cls, yaml_metric_path):
        stream = open(yaml_metric_path, 'r')
        try:
            specification = yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            cls.logger.exception(e) # TODO system exit

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
    def retrieve_licenses(cls, license_path):
        #The repository can be found at https://github.com/spdx/license-list-data
        #https://spdx.org/spdx-license-list/license-list-overview
        try:
            r = requests.get(license_path)
            try:
                if r.status_code == 200:
                    resp = r.json()
                    data = resp['licenses']
                    if data:
                        for d in data: #convert license name to lowercase
                            d['name'] =  d['name'].lower()
                        cls.all_licenses = data
                        cls.total_licenses = len(data)
                    # v = resp['licenseListVersion'] #TODO track version number, cache json locally;  cls.all_licenses=null if download failed
                    # d = resp['releaseDate']
            except json.decoder.JSONDecodeError as e1:
                cls.logger.exception(e1)
        except requests.exceptions.RequestException as e2: # TODO system exit
            cls.logger.exception(e2)

    @classmethod
    def get_licenses(cls):
        return cls.all_licenses

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
        for dictm in cls.all_metrics_list:
            new_dict[dictm['metric_identifier']] = {k: v for k, v in dictm.items() if k in wanted_fields}
        return new_dict
