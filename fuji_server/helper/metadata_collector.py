import enum
import logging
from typing import Optional

from fuji_server.helper import metadata_mapper
from fuji_server.helper.metadata_mapper import Mapper


class MetaDataCollector(object):
    metadata_mapping: Optional[Mapper]

    # Using enum class create enumerations of metadata sources
    class Sources(enum.Enum):
        DUBLINCORE = 'Embedded DublinCore'
        OPENGRAPH = 'Embedded OpenGraph'
        SCHEMAORG_EMBED = 'Schema.org JSON-LD (Embedded)'
        SCHEMAORG_NEGOTIATE = 'Schema.org JSON-LD (Datacite)'
        DATACITE_JSON = 'Datacite Search'
        SIGN_POSTING = 'Signposting Typed Links'
        LINKED_DATA ='Linked Data (RDF)'
        B2FIND = 'B2FIND Metadata Aggregator'

    def __init__(self, sourcemetadata: dict = None, mapping: metadata_mapper.Mapper = None, logger: logging.Logger = None):
        self.source_metadata = sourcemetadata
        self.metadata_mapping = mapping
        self.logger = logger
        self.target_metadata = {}

    @classmethod
    def getEnumSourceNames(cls) -> Sources:
        return cls.Sources

    def getMetadataMapping(self):
        return self.metadata_mapping

    def getLogger(self):
        return self.logger

    def setLogger(self, l):
        self.logger = l

    def getSourceMetadata(self):
        return self.source_metadata

    def setSourceMetadata(self, em):
        self.source_metadata = em

    def setTargetMetadata(self, tm):
        self.target_metadata = tm

    def getTargetMetadata(self):
        return self.target_metadata
