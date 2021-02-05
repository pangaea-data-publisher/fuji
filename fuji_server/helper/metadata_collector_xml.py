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

from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
import lxml
import re

class MetaDataCollectorXML (MetaDataCollector):
    target_url=None
    def __init__(self,  loggerinst, target_url, link_type='embedded'):
        self.target_url=target_url
        self.link_type = link_type
        super().__init__(logger=loggerinst)


    def parse_metadata(self):
        XSI = "http://www.w3.org/2001/XMLSchema-instance"
        if self.link_type == 'embedded':
            source_name = self.getEnumSourceNames().LINKED_DATA.value
        elif self.link_type == 'guessed':
            source_name = self.getEnumSourceNames().GUESSED_XML.value
        elif self.link_type == 'negotiated':
            source_name = self.getEnumSourceNames().XML_NEGOTIATED.value
        else:
            source_name = self.getEnumSourceNames().TYPED_LINK.value
        dc_core_metadata = None
        requestHelper = RequestHelper(self.target_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.xml)
        self.logger.info('FsF-F2-01M : Trying to access metadata from -: {}'.format(self.target_url))
        neg_source, xml_response = requestHelper.content_negotiate('FsF-F2-01M')
        if requestHelper.getHTTPResponse() is not None:
            self.logger.info('FsF-F2-01M : Extract metadata from -: {}'.format(source_name))
            #dom = lxml.html.fromstring(self.landing_html.encode('utf8'))
            if neg_source != 'xml':
                self.logger.info('FsF-F2-01M : Expected XML but content negotiation responded -: '+str(neg_source))
            else:
                tree = lxml.etree.XML(xml_response)
                schema_locations = set(tree.xpath("//*/@xsi:schemaLocation", namespaces={'xsi': XSI}))
                for schema_location in schema_locations:
                    self.namespaces=re.split('\s',schema_location)
                #TODO: implement some XSLT to handle the XML..

        return source_name, dc_core_metadata

