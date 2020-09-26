import enum
import logging
from typing import Optional

from fuji_server.helper import metadata_mapper
# MIT License
#
# Copyright (c) 2020 PANGAEA (https://www.pangaea.de/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from fuji_server.helper.metadata_mapper import Mapper


class MetaDataCollector(object):
    metadata_mapping: Optional[Mapper]

    # Using enum class create enumerations of metadata sources
    class Sources(enum.Enum):
        DUBLINCORE = 'Embedded DublinCore'
        OPENGRAPH = 'Embedded OpenGraph'
        SCHEMAORG_EMBED = 'Schema.org JSON-LD (Embedded)'
        SCHEMAORG_NEGOTIATE = 'Schema.org JSON-LD (Negotiated)'
        DATACITE_JSON = 'Datacite Search'
        SIGN_POSTING = 'Signposting Typed Links'
        RDF_SIGN_POSTING = 'RDF-based Typed Links'
        LINKED_DATA ='Linked Data (RDF)'
        B2FIND = 'B2FIND Metadata Aggregator'
        GUESSED_XML = 'Guessed XML Link'
        XML_NEGOTIATED = 'Generic XML (Negotiated)'
        RDFA = 'Embedded RDFa'
        MICRODATA = 'Embedded Microdata'

    def __init__(self, sourcemetadata: dict = None, mapping: metadata_mapper.Mapper = None, logger: logging.Logger = None):
        self.source_metadata = sourcemetadata
        self.metadata_mapping = mapping
        self.logger = logger
        self.target_metadata = {}
        self.namespaces = []

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

    def getNamespaces(self):
        return self.namespaces
