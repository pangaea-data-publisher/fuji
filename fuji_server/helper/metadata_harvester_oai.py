from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from lxml import etree

class OAIMetadataHarvester:

    oai_namespaces = {'oai': 'http://www.openarchives.org/OAI/2.0/'}

    def __init__(self, endpoint:str=None, loggerinst=None, metricid=None):
        self.oai_endpoint = endpoint
        #self.resource_identifier = resourceidentifier
        self.metric_id = metricid
        self.logger = loggerinst

    def getMetadataDC(self):
        #Resource Identifier	[]
        #The nature of a resource identifier is outside the scope of the OAI-PMH.
        #To facilitate access to the resource associated with harvested metadata, repositories should use an element in
        # #metadata records to establish a linkage between the record (and the identifier of its item) and the identifier
        # URL, URN, DOI, etc.) of the associated resource.
        # #The mandatory Dublin Core format provides the identifier element that should be used for this purpose
        return None

    def getMetadataStandards(self):
        filter =['datacite.org','openarchives.org','purl.org/dc/'] # TODO expand filters
        #http://ws.pangaea.de/oai/provider?verb=ListMetadataFormats
        self.oai_endpoint = self.oai_endpoint.split('?')[0]
        self.oai_endpoint = self.oai_endpoint.rstrip('/')
        oai_listmetadata_url = self.oai_endpoint+'?verb=ListMetadataFormats'
        requestHelper = RequestHelper(url=oai_listmetadata_url, logInst=self.logger)
        requestHelper.setAcceptType(AcceptTypes.xml)
        xml = requestHelper.content_negotiate(self.metric_id)
        root = etree.fromstring(xml.content)
        metadata_nodes = root.xpath('//oai:OAI-PMH/oai:ListMetadataFormats/oai:metadataFormat', namespaces=OAIMetadataHarvester.oai_namespaces)
        schemas = {}
        for node in metadata_nodes:
            ele = etree.XPathEvaluator(node, namespaces=OAIMetadataHarvester.oai_namespaces).evaluate
            metadata_prefix = ele('string(oai:metadataPrefix/text())') # <metadataPrefix>oai_dc</metadataPrefix>
            metadata_schema = ele('string(oai:schema/text())') #<schema>http://www.openarchives.org/OAI/2.0/oai_dc.xsd</schema>
            # TODO there can be more than one OAI-PMH endpoint, https://www.re3data.org/repository/r3d100011221
            if not any(s in metadata_schema for s in filter):
                schemas[metadata_prefix]= [metadata_schema]
            else:
                self.logger.info('FsF-R1.3-01M : Skipping non-disciplinary standard listed in OAIPMH - {}'.format(metadata_prefix))
        return schemas

