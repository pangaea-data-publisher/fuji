# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod

from urlextract import URLExtract

from fuji_server.helper.preprocessor import Preprocessor


class MetadataProvider(ABC):
    """
    An abstract base class for providing a metadata from an endpoint

    ...

    Attributes
    ----------
    logger : logging.Logger
        Logger object
    endpoint : str
        Endpoint url
    metric_id : str
        FUJI FAIR metric identifier
    namespaces : list
        List of namespace

    Methods
    -------
    getNamespaces()
        Abstract method
    getMetadata()
        Abstract method
    getMetadataStandards()
        Abstract method
    getNamespacefromIRIs(meta_source)
        Generate list of namespaces given IRI and store it class attributes of namespaces
    """

    def __init__(self, logger=None, endpoint=None, metric_id=None):
        """
        Parameters
        ----------
        logger : logging.Logger
            Logger object, default is None
        endpoint : str
            Endpoint url, default is None
        metric_id : str
            FUJI FAIR metric identifier, default is None
        """
        self.logger = logger
        self.endpoint = endpoint
        self.metric_id = metric_id
        self.namespaces = []
        super().__init__()

    @abstractmethod
    def getNamespaces(self):
        pass

    @abstractmethod
    def getMetadata(self):
        pass

    @abstractmethod
    def getMetadataStandards(self):
        pass

    def getNamespacesfromIRIs(self, meta_source):
        extractor = URLExtract()
        namespaces = set()
        if meta_source is not None:
            for url in set(extractor.gen_urls(str(meta_source))):
                namespace_candidate = url.rsplit("/", 1)[0]
                if namespace_candidate != url:
                    namespaces.add(namespace_candidate)
                else:
                    namespace_candidate = url.rsplit("#", 1)[0]
                    if namespace_candidate != url:
                        namespaces.add(namespace_candidate)

            vocabs = Preprocessor.getLinkedVocabs()
            lod_namespaces = [d["namespace"] for d in vocabs if "namespace" in d]
            for ns in namespaces:
                if ns + "/" in lod_namespaces:
                    self.namespaces.append(ns + "/")
                elif ns + "#" in lod_namespaces:
                    self.namespaces.append(ns + "#")
