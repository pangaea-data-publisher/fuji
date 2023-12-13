import logging
import os
import re

import yaml

from fuji_server.helper.preprocessor import Preprocessor


class MetricHelper:
    def __init__(self, metric_input_file_name, logger=None):
        self.metric_specification = "https://doi.org/10.5281/zenodo.6461229"
        self.formatted_specification = {}
        self.metric_file_name = metric_input_file_name
        self.metric_version = None
        self.total_metrics = 0
        self.all_metrics_list = None
         # match FsF or FAIR4RS metric (test) identifiers
        self.metric_regex = r"^FsF-[FAIR][0-9]?(\.[0-9])?-[0-9]+[MD]+|FRSM-[0-9]+-[FAIR][0-9]?(\.[0-9])?"
        self.metric_test_regex = r"FsF-[FAIR][0-9]?(\.[0-9])?-[0-9]+[MD]+(-[0-9]+[a-z]?)|^FRSM-[0-9]+-[FAIR][0-9]?(\.[0-9])?(?:-[a-zA-Z]+)?(-[0-9]+)?"
        self.config = {}
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()
        ym = re.match("(metrics_v)?([0-9]+\.[0-9]+)(_[a-z]+)?(\.yaml)?", metric_input_file_name)
        if ym:
            print(ym.groups())
            metric_file_name = ""
            self.metric_version = ym[2]
            if ym[3]:
                self.metric_version = ym[2] + ym[3]

            if not str(metric_input_file_name).endswith(".yaml"):
                metric_input_file_name = str(metric_input_file_name) + ".yaml"
            if not str(metric_input_file_name).startswith("metrics_v"):
                metric_input_file_name = "metrics_v" + metric_input_file_name
            if metric_input_file_name:
                metric_file_name = metric_input_file_name

            metric_yml_path = Preprocessor.METRIC_YML_PATH

            print("METRIC VERSION", self.metric_version)
            print("LOADING METRICS  ", metric_file_name, metric_yml_path)
            specification = {}
            try:
                stream = open(os.path.join(metric_yml_path, metric_file_name), encoding="utf8")
                specification = yaml.load(stream, Loader=yaml.FullLoader)
            except FileNotFoundError as e:
                print("ERROR: YAML LOADING ERROR -NOT FOUND")
                self.logger.error(e)
            except yaml.YAMLError as e:
                print("ERROR: YAML LOADING ERROR - YAML ERROR")
                self.logger.error(e)
            if specification:
                if specification.get("metric_specification"):
                    self.metric_specification = specification.get("metric_specification")
                self.config = specification.get("config")
                self.all_metrics_list = specification["metrics"]
                self.total_metrics = len(self.all_metrics_list)
                print("NUMBER OF LOADED METRICS  ", self.total_metrics)
                # expected output format of http://localhost:1071/uji/api/v1/metrics
                # unwanted_keys = ['question_type']
                self.formatted_specification["total"] = self.total_metrics
                self.formatted_specification["metrics"] = self.all_metrics_list
            else:
                print("ERROR: YAML FILE DOES NOT EXIST")
        else:
            print("ERROR: Invalid YAML File Name")
            self.logger.error("Invalid YAML File Name")

    def get_metrics_config(self):
        if self.config:
            return self.config
        else:
            return {}

    def get_custom_metrics(self, wanted_fields):
        new_dict = {}
        if self.all_metrics_list:
            for dictm in self.all_metrics_list:
                tm = re.search(self.metric_regex, str(dictm.get("metric_identifier")))
                if tm:
                    agnostic_identifier = tm[0]
                    new_dict[agnostic_identifier] = {k: v for k, v in dictm.items() if k in wanted_fields}
                    new_dict[agnostic_identifier]["agnostic_identifier"] = agnostic_identifier
                    new_dict[agnostic_identifier]["metric_identifier"] = dictm.get("metric_identifier")

                    if isinstance(dictm.get("metric_tests"), list):
                        for dictt in dictm.get("metric_tests"):
                            ttm = re.search(self.metric_test_regex, str(dictt.get("metric_test_identifier")))
                            if ttm:
                                agnostic_test_identifier = ttm[0]
                                dictt["agnostic_test_identifier"] = agnostic_test_identifier
                            else:
                                self.logger.error(
                                    "Invalid YAML defined Metric Test: " + str(dictt.get("metric_test_identifier"))
                                )
                else:
                    self.logger.error("Invalid YAML defined Metric: " + str(dictm.get("metric_identifier")))
        else:
            self.logger.error("No YAML defined Metric seems to exist: ")
        return new_dict

    def get_metric_version(self):
        return self.metric_version

    def get_metric(self, metric_id):
        metric = {}
        for listed_metric in self.all_metrics_list:
            if listed_metric.get("metric_identifier") == metric_id:
                metric = listed_metric
            else:
                for metric_test in listed_metric.get("metric_tests"):
                    if metric_test.get("metric_test_identifier") == metric_id:
                        metric = listed_metric
        return metric

    def get_metrics(self):
        return self.formatted_specification
