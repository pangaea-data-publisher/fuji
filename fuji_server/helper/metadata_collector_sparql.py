from fuji_server.helper.metadata_collector import MetaDataCollector


class MetaDataCollectorSparql (MetaDataCollector):

    def __init__(self, sourcemetadata, mapping, loggerinst):
        super().__init__(logger=loggerinst, mapping=mapping, sourcemetadata=sourcemetadata)

    def parse_metadata(self):

        return None
