import enum
import logging

class MetaDataCatalogue(object):

    apiURI = None
    # Using enum class create enumerations of metadata catalogs

    class Sources(enum.Enum):
        DATACITE = 'DataCite Registry'
        GOOGLE_DATASET = 'Google Dataset Search'
        MENDELEY_DATA = 'Mendeley Data'

    def __init__(self,logger: logging.Logger = None):
        self.logger = logger
        self.islisted = False
        self.source = None

    @classmethod
    def getEnumSourceNames(cls) -> Sources:
        return cls.Sources

    def query(self, pid):
        response = None
        return response
