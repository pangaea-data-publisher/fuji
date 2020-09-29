from abc import ABC, abstractmethod


class MetadataProvider(ABC):

    def __init__(self, logger=None, endpoint=None, metric_id=None):
        self.logger = logger
        self.endpoint = endpoint
        self.metric_id = metric_id
        self.namespaces = []
        super(MetadataProvider, self).__init__()

    @abstractmethod
    def getNamespaces(self):
        pass

    @abstractmethod
    def getMetadata(self):
        pass
