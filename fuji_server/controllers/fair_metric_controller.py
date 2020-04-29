from fuji_server.controllers.preprocessor import Preprocessor
from fuji_server.models.metrics import Metrics  # noqa: E501


def get_metrics():  # noqa: E501
    """Return all metrics and their definitions
     # noqa: E501
    :rtype: Metrics
    """
    response = Preprocessor.get_metrics()
    return response, 200

