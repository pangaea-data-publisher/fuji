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

from fuji_server.helper.metadata_provider import MetadataProvider
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from lxml import etree


class OGCCSWMetadataProvider(MetadataProvider):

    csw_namespaces = {
        'csw': 'http://www.opengis.net/cat/csw/2.0.2',
        'ogc': 'http://www.opengis.net/ogc',
        'ows': 'http://www.opengis.net/ows',
        'gmd': 'http://www.isotc211.org/2005/gmd'
    }

    def getMetadata(self):
        # http://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:pangaea.de:doi:10.1594/PANGAEA.66871
        #The nature of a resource identifier is outside the scope of the OAI-PMH.
        #To facilitate access to the resource associated with harvested metadata, repositories should use an element in
        # #metadata records to establish a linkage between the record (and the identifier of its item) and the identifier
        # URL, URN, DOI, etc.) of the associated resource.
        # #The mandatory Dublin Core format provides the identifier element that should be used for this purpose
        return None

    def getMetadataStandards(self):
        csw_endpoint = self.endpoint.split('?')[0]
        csw_listmetadata_url = csw_endpoint + '?service=CSW&request=GetCapabilities'
        requestHelper = RequestHelper(url=csw_listmetadata_url, logInst=self.logger)
        requestHelper.setAcceptType(AcceptTypes.xml)
        response_type, xml = requestHelper.content_negotiate(self.metric_id)
        schemas = {}
        if xml:
            try:
                root = etree.fromstring(requestHelper.response_content)
                metadata_nodes = root.xpath('//ows:Parameter[@name="outputSchema"]/ows:Value',
                                            namespaces=OGCCSWMetadataProvider.csw_namespaces)
                for node in metadata_nodes:
                    if node.text:
                        if node.text not in self.namespaces:
                            self.namespaces.append(str(node.text))
                            schemas[str(node.text)] = str(node.text)
            except:
                self.logger.info('{0} : Could not parse XML response retrieved from OGC CSW endpoint'.format(
                    self.metric_id))

        return schemas

    def getNamespaces(self):
        return self.namespaces
