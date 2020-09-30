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

class OAIMetadataProvider(MetadataProvider):

    oai_namespaces = {'oai': 'http://www.openarchives.org/OAI/2.0/'}

    def getMetadata(self):
        # http://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:pangaea.de:doi:10.1594/PANGAEA.66871
        #The nature of a resource identifier is outside the scope of the OAI-PMH.
        #To facilitate access to the resource associated with harvested metadata, repositories should use an element in
        # #metadata records to establish a linkage between the record (and the identifier of its item) and the identifier
        # URL, URN, DOI, etc.) of the associated resource.
        # #The mandatory Dublin Core format provides the identifier element that should be used for this purpose
        return None

    def getMetadataStandards(self):
        filter =['datacite.org','openarchives.org','purl.org/dc/'] # TODO expand filters
        #http://ws.pangaea.de/oai/provider?verb=ListMetadataFormats
        oai_endpoint = self.endpoint.split('?')[0]
        #oai_endpoint = oai_endpoint.rstrip('/')
        oai_listmetadata_url = oai_endpoint+'?verb=ListMetadataFormats'
        requestHelper = RequestHelper(url=oai_listmetadata_url, logInst=self.logger)
        requestHelper.setAcceptType(AcceptTypes.xml)
        response_type, xml = requestHelper.content_negotiate(self.metric_id)
        schemas = {}
        if xml:
            root = etree.fromstring(xml.content)
            metadata_nodes = root.xpath('//oai:OAI-PMH/oai:ListMetadataFormats/oai:metadataFormat', namespaces=OAIMetadataProvider.oai_namespaces)
            for node in metadata_nodes:
                ele = etree.XPathEvaluator(node, namespaces=OAIMetadataProvider.oai_namespaces).evaluate
                metadata_prefix = ele('string(oai:metadataPrefix/text())') # <metadataPrefix>oai_dc</metadataPrefix>
                metadata_schema = ele('string(oai:schema/text())') #<schema>http://www.openarchives.org/OAI/2.0/oai_dc.xsd</schema>
                metadata_schema = metadata_schema.strip()
                self.namespaces.append(metadata_schema)
                # TODO there can be more than one OAI-PMH endpoint, https://www.re3data.org/repository/r3d100011221
                if not any(s in metadata_schema for s in filter):
                    schemas[metadata_prefix]= [metadata_schema]
                else:
                    self.logger.info('{0} : Skipped domain-agnostic standard listed in OAI-PMH endpoint - {1}'.format(self.metric_id,metadata_prefix))
        return schemas

    def getNamespaces(self):
        return self.namespaces