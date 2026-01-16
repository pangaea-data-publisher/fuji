# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT


class CompatibiltyHelper:
    # helps to find the correct metric after the numbering changed a bit for metric 0.8
    def __init__(self, metric_version=0):
        self.logger_target = {
            "pid": "FsF-F1-02D",
            "metadata_properties": "FsF-F2-01M",
            "data_id": "FsF-F3-01M",
            "related": "FsF-I3-01M",
            "metadata_standard": "FsF-R1.3-01M",
        }
        self.metric_version = metric_version
        self.metric_shift = {"FsF-F1-02D": "FsF-F1-02MD"}

    def get_metric(self, metric_id):
        if metric_id in self.logger_target:
            metric_id = self.logger_target[metric_id]
        if self.metric_version >= 0.8:
            if self.metric_shift.get(metric_id):
                metric_id = self.metric_shift[metric_id]
        return metric_id
