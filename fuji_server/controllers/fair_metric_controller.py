# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.helper.metric_helper import MetricHelper


def get_metrics(version):
    """Return all metrics and their definitions.
    :rtype: Metrics
    """
    metric_version = version
    metric_helper = MetricHelper(metric_version)
    response = metric_helper.get_metrics()
    if response:
        return response, 200
    else:
        return response, 404


def get_metric(version, metric):
    """Return all metrics and their definitions.
    :rtype: Metrics
    """
    metric_version = version
    metric_helper = MetricHelper(metric_version)
    response = metric_helper.get_metric(metric)
    if response:
        return response, 200
    else:
        return response, 404
