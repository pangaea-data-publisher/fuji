import logging

import jmespath
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


class MetaDataCollectorMicroData (MetaDataCollector):
    source_name=None
    def __init__(self, sourcemetadata, mapping, loggerinst):
        super().__init__(logger=loggerinst, mapping=mapping, sourcemetadata=sourcemetadata)

    def parse_metadata(self):
        micro_metadata = {}
        ext_meta=None
        if self.source_metadata:
            self.source_name = self.getEnumSourceNames().MICRODATA.value
            ext_meta = self.source_metadata[0]

        if ext_meta is not None:
            self.logger.info('FsF-F2-01M : Extract metadata from -: {}'.format(self.source_name))
            # TODO check syntax - not ending with /, type and @type
            # TODO (important) extend mapping to detect other pids (link to related entities)?
            # TODO replace check_context_type list context comparison by regex
            check_context_type =  ["Dataset", "Collection"]
            try:
                #if ext_meta['@context'] in check_context_type['@context'] and ext_meta['@type'] in check_context_type["@type"]:
                if str(ext_meta.get('type')).find('schema.org') > -1:
                    micro_metadata = jmespath.search(self.metadata_mapping.value, ext_meta)
                    self.namespaces.append('http://schema.org/')
                else:
                    self.logger.info('FsF-F2-01M : Failed to parse non schema.org type Microdata')
            except Exception as err:
                #print(err.with_traceback())
                self.logger.info('FsF-F2-01M : Failed to parse Microdata -: {}'.format(err))
        else:
            self.logger.info('FsF-F2-01M : Could not identify Microdata metadata')

        return self.source_name, micro_metadata