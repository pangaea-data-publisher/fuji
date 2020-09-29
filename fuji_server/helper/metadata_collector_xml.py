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
        dc_core_metadata = None
        requestHelper: RequestHelper = RequestHelper(self.target_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.xml)
        neg_source, xml_response = requestHelper.content_negotiate('FsF-F2-01M')
        self.logger.info('FsF-F2-01M : Extract metadata from {}'.format(source_name))
        #dom = lxml.html.fromstring(self.landing_html.encode('utf8'))
        if neg_source != 'xml':
            self.logger.info('FsF-F2-01M : Expected XML but content negotiation responded: '+str(neg_source))
        else:
            tree = lxml.etree.XML(xml_response.content)
            schema_locations = set(tree.xpath("//*/@xsi:schemaLocation", namespaces={'xsi': XSI}))
            for schema_location in schema_locations:
                self.namespaces=re.split('\s',schema_location)
            #TODO: implement some XSLT to handle the XML..

        return source_name, dc_core_metadata

