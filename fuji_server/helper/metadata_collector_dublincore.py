import re

from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.metadata_collector import MetaDataCollector


class MetaDataCollectorDublinCore (MetaDataCollector):

    def __init__(self, sourcemetadata, mapping, loggerinst):
        super().__init__(logger=loggerinst, mapping=mapping, sourcemetadata=sourcemetadata)

    def parse_metadata(self):
        dc_core_metadata = {}
        source = None
        if self.source_metadata is not None:
            try:
                self.logger.info('FsF-F2-01M : Extract DublinCore metadata from html page')
                # get core metadat from dublin core meta tags:
                # < meta name = "DCTERMS.element" content = "Value" / >
                # meta_dc_matches = re.findall('<meta\s+([^\>]*)name=\"(DC|DCTERMS)?\.([a-z]+)\"(.*?)content=\"(.*?)\"',self.landing_html)
                exp = '<\s*meta\s*([^\>]*)name\s*=\s*\"(DC|DCTERMS)?\.([A-Za-z]+)\"(.*?)content\s*=\s*\"(.*?)\"'
                meta_dc_matches = re.findall(exp, self.source_metadata)
                if len(meta_dc_matches) > 0:
                    source = self.getEnumSourceNames().DUBLINCORE.value
                    for dc_meta in meta_dc_matches:
                        # dc_meta --> ('', 'DC', 'creator', ' ', 'Hillenbrand, Claus-Dieter')
                        k = dc_meta[2]
                        v = dc_meta[4]
                        # if self.isDebug:
                        #   self.logger.info('FsF-F2-01M: DublinCore metadata element, %s = %s , ' % (k, v)
                        if k in self.metadata_mapping.value.values():
                            self.logger.info('FsF-F2-01M: DublinCore metadata element, %s = %s , ' % (k, v))
                            elem = [key for (key, value) in Mapper.DC_MAPPING.value.items() if value == k][0]
                            if elem in dc_core_metadata:
                                if isinstance(dc_core_metadata[elem], list):
                                    dc_core_metadata[elem].append(v)
                                else:  # string
                                    temp_list = []
                                    temp_list.append(dc_core_metadata[elem])
                                    temp_list.append(v)
                                    dc_core_metadata[elem] = temp_list
                            else:
                                dc_core_metadata[elem] = v
            except Exception as e:
                self.logger.exception('Failed to extract DublinCore - {}'.format(e))
        return source, dc_core_metadata
