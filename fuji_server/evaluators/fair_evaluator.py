import logging

from fuji_server.models.fair_result_common_score import FAIRResultCommonScore

from fuji_server.helper.log_message_filter import MessageFilter

class FAIREvaluator:
    def __init__(self, fuji_instance):
        self.fuji=fuji_instance
        self.metric_identifier = None
        self.metrics = None
        self.result = None
        self.isDebug=self.fuji.isDebug
        self.count = self.fuji.count
        self.logger = self.fuji.logger
        if self.isDebug == True:
            self.msg_filter = MessageFilter()
            self.logger.addFilter(self.msg_filter)
            self.logger.setLevel(logging.INFO)  # set to debug in testing environment

    def set_metric(self, metric_identifier, metrics):
        self.metrics = metrics
        self.metric_identifier = metric_identifier
        if self.metric_identifier is not None:
            self.total_score = int(self.metrics.get(metric_identifier).get('total_score'))
            self.score = FAIRResultCommonScore(total=self.total_score)
            self.metric_name = self.metrics.get(metric_identifier).get('metric_name')

    def evaluate(self):
        #Do the main FAIR check here
         return True

    def getResult(self):
        self.evaluate()
        if self.isDebug:
            self.result.test_debug = self.msg_filter.getMessage(self.metric_identifier)
        return self.result.to_dict()