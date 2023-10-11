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

from urlextract import URLExtract

from fuji_server.helper import metadata_mapper
from fuji_server.helper.linked_vocab_helper import linked_vocab_helper
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.preprocessor import Preprocessor


class MetadataFormats(enum.Enum):
    HTML = {"label": "HTML", "acronym": "html"}
    XHTML = {"label": "XHTML", "acronym": "xhtml"}
    XML = {"label": "XML", "acronym": "xml"}
    RDF = {"label": "RDF", "acronym": "rdf"}
    RDFA = {"label": "RDFa", "acronym": "rdfa"}
    JSON = {"label": "JSON", "acronym": "json"}
    JSONLD = {"label": "JSON-LD", "acronym": "json-ld"}
    MICRODATA = {"label": "MICRODATA", "acronym": "microdata"}
    TEXT = {"label": "Text", "acronym": "text"}

    def acronym(self):
        return self.value.get("acronym")


class MetadataOfferingMethods(enum.Enum):
    HTML_EMBEDDING = {"label": "HTML Embedding", "acronym": "html_embedding"}
    MICRODATA_RDFA = {"label": "Microdata and RDFa", "acronym": "microdata_rdfa"}
    TYPED_LINKS = {"label": "Typed Links", "acronym": "typed_links"}
    SIGNPOSTING = {"label": "Signposting Links", "acronym": "signposting"}
    CONTENT_NEGOTIATION = {"label": "Content Negotiation", "acronym": "content_negotiation"}

    def acronym(self):
        return self.value.get("acronym")


# Using enum class create enumerations of metadata sources
class MetadataSources(enum.Enum):
    """ "Enum class to enumerate metadata sources."""

    @classmethod
    def getSourcesbyMethod(cls, methods):
        found_sources = []
        if not isinstance(methods, list):
            methods = [methods]
        for method in methods:
            if isinstance(method, str):
                method = MetadataOfferingMethods[method]
            for ms in MetadataSources:
                if ms.value.get("method") == method:
                    found_sources.append(ms)
        return found_sources

    HIGHWIRE_EPRINTS_EMBEDDED = {
        "method": MetadataOfferingMethods.HTML_EMBEDDING,
        "label": "Embedded Highwire or Eprints",
        "acronym": "highwire-eprints-html",
        "format": MetadataFormats.HTML,
    }
    DUBLINCORE_EMBEDDED = {
        "method": MetadataOfferingMethods.HTML_EMBEDDING,
        "label": "Embedded DublinCore",
        "acronym": "dublincore-html",
        "format": MetadataFormats.XHTML,
    }
    OPENGRAPH_EMBEDDED = {
        "method": MetadataOfferingMethods.HTML_EMBEDDING,
        "label": "Embedded OpenGraph",
        "acronym": "opengraph-html",
        "format": MetadataFormats.RDFA,
    }  # OpenGraph is based on RDFa
    SCHEMAORG_EMBEDDED = {
        "method": MetadataOfferingMethods.HTML_EMBEDDING,
        "label": "Schema.org JSON-LD (Embedded)",
        "acronym": "schemaorg-html",
        "format": MetadataFormats.JSONLD,
    }
    RDFA_EMBEDDED = {
        "method": MetadataOfferingMethods.MICRODATA_RDFA,
        "label": "Embedded RDFa",
        "acronym": "rdfa-html",
        "format": MetadataFormats.RDFA,
    }
    MICRODATA_EMBEDDED = {
        "method": MetadataOfferingMethods.MICRODATA_RDFA,
        "label": "Embedded Microdata",
        "acronym": "microdata-html",
        "format": MetadataFormats.MICRODATA,
    }
    SCHEMAORG_NEGOTIATED = {
        "method": MetadataOfferingMethods.CONTENT_NEGOTIATION,
        "label": "Schema.org JSON-LD (Negotiated)",
        "acronym": "schemaorg-negotiated",
        "format": MetadataFormats.JSONLD,
    }
    DATACITE_JSON_NEGOTIATED = {
        "method": MetadataOfferingMethods.CONTENT_NEGOTIATION,
        "label": "Datacite Search",
        "acronym": "datacite-negotiated",
        "format": "JSON",
    }
    RDF_NEGOTIATED = {
        "method": MetadataOfferingMethods.CONTENT_NEGOTIATION,
        "label": "Linked Data (RDF)",
        "acronym": "rdf-negotiated",
        "format": MetadataFormats.RDF,
    }
    XML_NEGOTIATED = {
        "method": MetadataOfferingMethods.CONTENT_NEGOTIATION,
        "label": "Generic XML (Negotiated)",
        "acronym": "xml-negotiated",
        "format": MetadataFormats.XML,
    }
    XML_TYPED_LINKS = {
        "method": MetadataOfferingMethods.TYPED_LINKS,
        "label": "Generic XML, Typed Links",
        "acronym": "xml-type-linked",
        "format": MetadataFormats.XML,
    }
    RDF_TYPED_LINKS = {
        "method": MetadataOfferingMethods.TYPED_LINKS,
        "label": "Linked Data (RDF), Typed Links",
        "acronym": "rdf-type-linked",
        "format": MetadataFormats.RDF,
    }  # Links in header which lead to a RDF resource
    SCHEMAORG_TYPED_LINKS = {
        "method": MetadataOfferingMethods.TYPED_LINKS,
        "label": "Schema.org JSON-LD, Typed Links",
        "acronym": "schemaorg-type-linked",
        "format": MetadataFormats.JSONLD,
    }
    # TYPED_LINK = 'Typed Links'
    SIGNPOSTING_LINKS = {
        "method": MetadataOfferingMethods.SIGNPOSTING,
        "label": "Signposting Typed Links",
        "acronym": "signposting-linked",
    }
    RDF_SIGNPOSTING_LINKS = {
        "method": MetadataOfferingMethods.SIGNPOSTING,
        "label": "Linked Data (RDF), Signposting Links",
        "acronym": "rdf-signposting-linked",
        "format": MetadataFormats.RDF,
    }
    XML_SIGNPOSTING_LINKS = {
        "method": MetadataOfferingMethods.SIGNPOSTING,
        "label": "Generic XML, Signposting Links",
        "acronym": "xml-signposting-linked",
        "format": MetadataFormats.XML,
    }
    # B2FIND = 'B2FIND Metadata Aggregator'
    XML_GUESSED = {"method": None, "label": "Guessed XML Link", "acronym": "xml-guessed", "format": MetadataFormats.XML}
    OAI_ORE = {"method": MetadataOfferingMethods.TYPED_LINKS, "label": "OAI-ORE", "format": MetadataFormats.XML}

    def acronym(self):
        return self.value.get("acronym")

    def format(self):
        return self.value.get("format")


class MetaDataCollector:
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

    metadata_mapping: Mapper | None

    def __init__(
        self, sourcemetadata: dict = None, mapping: metadata_mapper.Mapper = None, logger: logging.Logger = None
    ):
        """
        Parameters
        ----------
        sourcemetadata : dict, optional
            Metadata souce in a dictionary, default is None
        mapping : metadata_mapper.Mapper, optional
            Metadata mapping to metadata sources, default is None
        logger : logging.Logger, optional
            Logger object, default is None
        """
        self.source_metadata = sourcemetadata
        self.metadata_mapping = mapping
        self.metadata_format = None
        self.logger = logger
        self.target_metadata = {}
        # namespaces used in the declaration parts
        self.namespaces = []
        # namespaces recognized in lonked URIs
        self.linked_namespaces = {}
        self.content_type = None
        self.uris = []
        self.auth_token_type = "Basic"
        self.auth_token = None
        self.accept_type = None

    @classmethod
    def getEnumSourceNames(cls) -> MetadataSources:
        return MetadataSources

    @classmethod
    def getEnumMethodNames(cls) -> MetadataOfferingMethods:
        return MetadataOfferingMethods

    def setAcceptType(self, type):
        self.accept_type = type

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

    def getLinkedNamespaces(self):
        return self.linked_namespaces

    def getContentType(self):
        return self.content_type

    def setLinkedNamespaces(self, meta_source):
        """Return the Namespaces given the Internatiolized Resource Identifiers(IRIs)

        Parameters
        ----------
        meta_source:str or lst
        """
        extractor = URLExtract()
        found_urls = []
        lov_helper = linked_vocab_helper(Preprocessor.linked_vocab_index)
        if meta_source is not None:
            if isinstance(meta_source, str):
                found_urls = set(extractor.gen_urls(str(meta_source)))
            elif isinstance(meta_source, list):
                found_urls = set(meta_source)
            for url in found_urls:
                if isinstance(url, str):
                    found_lov = lov_helper.get_linked_vocab_by_iri(url)
                    if found_lov:
                        self.linked_namespaces[found_lov.get("namespace")] = found_lov

    def set_auth_token(self, authtoken, authtokentype):
        self.auth_token = authtoken
        self.auth_token_type = authtokentype
