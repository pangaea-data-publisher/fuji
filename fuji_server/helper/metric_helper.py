import logging
import os
import re

import yaml

from fuji_server.helper.preprocessor import Preprocessor

class MetricHelper:
    def __init__(self, metric_file_name, logger=None):
        self.metric_specification = None
        self.formatted_specification = {}
        self.metric_file_name = metric_file_name
        self.metric_version = None
        self.total_metrics = 0
        self.all_metrics_list = None

        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()
        ym = re.match('metrics_v([0-9]+\.[0-9]+)(_[a-z]+)?\.yaml', metric_file_name)
        if ym:
            self.metric_version = float(ym[1])
            print('METRIC VERSION' , self.metric_version)
            print('LOADING METRICS  ', metric_file_name)

            metric_yml_path  = os.path.join(Preprocessor.METRIC_YML_PATH,  metric_file_name)
            stream = open(metric_yml_path, 'r', encoding='utf8')
            try:
                specification = yaml.load(stream, Loader=yaml.FullLoader)
            except yaml.YAMLError as e:
                self.logger.error(e)
            self.metric_specification = specification.get('metric_specification')

            self.all_metrics_list = specification['metrics']
            self.total_metrics = len(self.all_metrics_list)
            print('LOADED METRICS  ', self.total_metrics)
            # expected output format of http://localhost:1071/uji/api/v1/metrics
            # unwanted_keys = ['question_type']
            self.formatted_specification['total'] = self.total_metrics
            self.formatted_specification['metrics'] = self.all_metrics_list
        else:
            print('Invalid YAML File Name')
            self.logger.error('Invalid YAML File Name')

    def get_custom_metrics(self, wanted_fields):
        new_dict = {}
        if not self.all_metrics_list:
            self.retrieve_metrics_yaml(self.METRIC_YML_PATH)
        for dictm in self.all_metrics_list:
            new_dict[dictm['metric_identifier']] = {k: v for k, v in dictm.items() if k in wanted_fields}
        return new_dict

    def get_metric_version(self):
        return self.metric_version