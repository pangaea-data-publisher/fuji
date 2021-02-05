import json
import logging

import jmespath
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


class MetaDataCollectorOpenGraph (MetaDataCollector):
    source_name=None
    def __init__(self, sourcemetadata, mapping, loggerinst):
        super().__init__(logger=loggerinst, mapping=mapping, sourcemetadata=sourcemetadata)

    def parse_metadata(self):
        og_metadata = {}
        ext_meta=None
        if self.source_metadata:
            self.logger.info('FsF-F2-01M : Extract metadata from -: {}'.format(self.source_name))
            self.source_name = self.getEnumSourceNames().OPENGRAPH.value
            ext_meta =dict(self.source_metadata[0].get('properties'))
        if ext_meta is not None:
            self.logger.info('FsF-F2-01M : Found OpenGraph metadata')
            for map_key, map_value in self.metadata_mapping.value.items():
                og_metadata[map_key] = ext_meta.get(map_value)
            self.namespaces.append('http://ogp.me/ns#')
        else:
            self.logger.info('FsF-F2-01M : Could not identify OpenGraph metadata')

        return self.source_name, og_metadata