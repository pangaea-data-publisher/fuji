# -*- coding: utf-8 -*-

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

import enum
import logging
from typing import Optional
from urlextract import URLExtract
from fuji_server.helper import metadata_mapper
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.preprocessor import Preprocessor


class MetaDataCollector(object):

    metadata_mapping: Optional[Mapper]
    """
    A class to collect a metadata from different metadata sources.

    ...

    Attributes
    ----------
    metadata_mapping : Mapper, optional
    Sources : enum.Enum
        Enum class to enumerate metadata sources
    source_metadata : dict
        Metadata souce in a dictionary.
    metadata_mapping : metadata_mapper.Mapper
        Metadata mapping to metadata sources
    logger : logging.Logger
    target_metadata : dict
    namespaces : list
        List of namespace.

    Methods
    -------
    getEnumSourceNames()
        Class method returning the source names.
    getMetadataMapping()
        Get/return the metadata mapping.
    getLogger()
        Get/return the logger object.
    setLogger(l)
        Set the logger according to inpur paramter l.
    getSourceMetadata()
        Get source metadata.
    setSourceMetadata(em)
        Set the source metadata according to input parameter em.
    setTargetMetadata(tm)
        Set the target metadata according to input parameter tm.
    getTargetMetadata()
        Returm the target metadata.
    getNamespaces()
        Return the namespaces of the metadata.
    getNamespacesfromIRIs(meta_source)
        Return the Namespaces given the Internatiolized Resource Identifiers(IRIs)
    """

    # Using enum class create enumerations of metadata sources
    class Sources(enum.Enum):
        """"Enum class to enumerate metadata sources."""
        DUBLINCORE = 'Embedded DublinCore'
        OPENGRAPH = 'Embedded OpenGraph'
        SCHEMAORG_EMBED = 'Schema.org JSON-LD (Embedded)'
        SCHEMAORG_NEGOTIATE = 'Schema.org JSON-LD (Negotiated)'
        DATACITE_JSON = 'Datacite Search'
        TYPED_LINK = 'Typed Links'
        SIGN_POSTING = 'Signposting Typed Links'
        RDF_TYPED_LINKS = 'RDF-based Typed Links'  #Links in header which lead to a RDF resource
        LINKED_DATA = 'Linked Data (RDF)'
        B2FIND = 'B2FIND Metadata Aggregator'
        GUESSED_XML = 'Guessed XML Link'
        XML_NEGOTIATED = 'Generic XML (Negotiated)'
        RDFA = 'Embedded RDFa'
        MICRODATA = 'Embedded Microdata'
        OAI_ORE = 'OAI-ORE'

    def __init__(self,
                 sourcemetadata: dict = None,
                 mapping: metadata_mapper.Mapper = None,
                 logger: logging.Logger = None):
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

    def getNamespacesfromIRIs(self, meta_source):
        extractor = URLExtract()
        namespaces = set()
        if meta_source is not None:
            for url in set(extractor.gen_urls(str(meta_source))):
                namespace_candidate = url.rsplit('/', 1)[0]
                if namespace_candidate != url:
                    namespaces.add(namespace_candidate)
                else:
                    namespace_candidate = url.rsplit('#', 1)[0]
                    if namespace_candidate != url:
                        namespaces.add(namespace_candidate)

            vocabs = Preprocessor.getLinkedVocabs()
            lod_namespaces = [d['namespace'] for d in vocabs if 'namespace' in d]
            for ns in namespaces:
                if ns + '/' in lod_namespaces:
                    self.namespaces.append(ns + '/')
                elif ns + '#' in lod_namespaces:
                    self.namespaces.append(ns + '#')
