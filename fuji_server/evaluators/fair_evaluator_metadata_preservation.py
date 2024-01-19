# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.metadata_preserved import MetadataPreserved
from fuji_server.models.metadata_preserved_output import MetadataPreservedOutput


class FAIREvaluatorMetadataPreserved(FAIREvaluator):
    """
    A class to evaluate that the metadata remains available, even if the data is no longer available (A2-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()

    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FsF-A2-01M-1", "FRSM-08-F4"])

    def evaluate(self):
        registry_bound_pid = ["doi"]
        self.result = MetadataPreserved(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        outputs = []
        test_status = "fail"
        score = 0
        if self.fuji.pid_scheme:
            if self.fuji.pid_scheme in registry_bound_pid:
                test_status = "pass"
                outputs.append(MetadataPreservedOutput(metadata_preservation_method="datacite"))
                score = 1
                self.setEvaluationCriteriumScore("FsF-A2-01M-1", 1, "pass")
                self.maturity = 3
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    "{0} : Metadata registry bound PID system used: "
                    + self.fuji.pid_scheme.format(self.metric_identifier),
                )
            else:
                self.logger.warning(f"{self.metric_identifier} : NO metadata registry bound PID system used")
        self.score.earned = score
        self.result.score = self.score
        self.result.output = outputs
        self.result.metric_tests = self.metric_tests
        self.result.test_status = test_status
        self.result.maturity = self.maturity
