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

from abc import ABC, abstractmethod

from urlextract import URLExtract

from fuji_server.helper.preprocessor import Preprocessor


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

    @abstractmethod
    def getMetadataStandards(self):
        pass

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
                if ns+'/' in lod_namespaces:
                    self.namespaces.append(ns+'/')
                elif ns+'#' in lod_namespaces:
                    self.namespaces.append(ns+'#')
