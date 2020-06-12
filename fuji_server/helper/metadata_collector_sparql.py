from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes

class MetaDataCollectorSparql (MetaDataCollector):
    target_url=None
    def __init__(self, mapping, loggerinst, target_url):
        self.target_url=target_url
        super().__init__(logger=loggerinst, mapping=mapping)

    def parse_metadata(self, ):
        requestHelper: RequestHelper = RequestHelper(self.target_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.rdf)
        rdf_meta = requestHelper.content_negotiate('FsF-F2-01M')
        if rdf_meta is not None:
            # TODO: set credit score for being valid RDF
            # TODO: since its valid RDF aka semantic representation, make sure FsF-I1-01M is passed and scored
            #rdf_meta.query(self.metadata_mapping.value)
            print(rdf_meta)
        return None
