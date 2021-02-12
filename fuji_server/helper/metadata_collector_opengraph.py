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
            #self.logger.info('FsF-F2-01M : Trying to extract OpenGraph metadata from html page')
            self.source_name = self.getEnumSourceNames().OPENGRAPH.value
            ext_meta =dict(self.source_metadata[0].get('properties'))
        if ext_meta is not None:
            for map_key, map_value in self.metadata_mapping.value.items():
                if ext_meta.get(map_value):
                    og_metadata[map_key] = ext_meta.get(map_value)
            if len(og_metadata) >0:
                self.logger.info('FsF-F2-01M : Found OpenGraph metadata-: ' + str(og_metadata.keys()))
                self.namespaces.append('http://ogp.me/ns#')
            #else:
            #    self.logger.info('FsF-F2-01M : Non-metadata OpenGraph properties -:'+str(ext_meta))
            self.logger.info('FsF-F2-01M : Could not identify OpenGraph metadata')

        return self.source_name, og_metadata