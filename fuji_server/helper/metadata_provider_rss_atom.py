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
import re

import feedparser
import lxml

from fuji_server.helper.metadata_provider import MetadataProvider
from fuji_server.helper.request_helper import AcceptTypes, RequestHelper


class RSSAtomMetadataProvider(MetadataProvider):
    """A metadata provider class to provide the metadata from GeoRSS ATOM

    ...

    Methods
    -------
    getMetadataStandards()
        Method will return the metadata standards in the namespaces
    getMetadata(queryString)
        Method that will return schemas of GeoRSS Atom
    getNamespaces()
        Method to get namespaces

    """

    rss_namespaces = {"atom": "http://www.w3.org/2005/Atom", "georss": "http://www.georss.org/georss/"}

    def getMetadata(self):
        # http://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:pangaea.de:doi:10.1594/PANGAEA.66871
        # The nature of a resource identifier is outside the scope of the OAI-PMH.
        # To facilitate access to the resource associated with harvested metadata, repositories should use an element in
        # #metadata records to establish a linkage between the record (and the identifier of its item) and the identifier
        # URL, URN, DOI, etc.) of the associated resource.
        # #The mandatory Dublin Core format provides the identifier element that should be used for this purpose
        return None

    def getMetadataStandards(self):
        """Method to get the metadata schema from the GeoRSS Atom namespaces

        Returns
        -------
        dict
            A dictionary of schemas in GeoRSS Atom
        """
        schemas = {}
        XSI = "http://www.w3.org/2001/XMLSchema-instance"

        try:
            requestHelper = RequestHelper(self.endpoint, self.logger)
            requestHelper.setAcceptType(AcceptTypes.default)
            neg_source, rss_response = requestHelper.content_negotiate("FsF-F2-01M")
            if requestHelper.response_content is not None:
                feed = feedparser.parse(requestHelper.response_content)
            # print(feed.namespaces)
            for namespace_pre, namespace_uri in feed.namespaces.items():
                if namespace_uri not in self.namespaces:
                    self.namespaces.append(str(namespace_uri))
                    schemas[str(namespace_pre)] = str(namespace_uri)
        except Exception as e:
            print("RSS Error ", e)
            self.logger.info(
                "{0} : Could not parse response retrieved from RSS/Atom Feed endpoint -: {1}".format(
                    self.metric_id, str(e)
                )
            )

        return schemas

    def getNamespaces(self):
        return self.namespaces
