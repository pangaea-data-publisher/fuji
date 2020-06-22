import re
from typing import List

import jmespath

from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


class MetaDataCollectorDatacite (MetaDataCollector):

    exclude_conversion: List[str]

    def __init__(self, mapping, pid_url=None, loggerinst=None):
        super().__init__(logger=loggerinst, mapping=mapping)
        self.pid_url = pid_url
        self.exclude_conversion = ['creator', 'license', 'related_resources']

    def parse_metadata(self):
        source_name = None
        dcite_metadata = {}
        self.logger.info('FsF-F2-01M : Extract datacite metadata')
        requestHelper = RequestHelper(self.pid_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.datacite_json)
        ext_meta = requestHelper.content_negotiate('FsF-F2-01M')
        if ext_meta:
            try:
                dcite_metadata = jmespath.search(self.metadata_mapping.value, ext_meta)
                if dcite_metadata:
                    self.namespaces.append('http://datacite.org/schema/')
                    source_name = self.getEnumSourceNames().DATACITE_JSON.value
                    if dcite_metadata['creator'] is None:
                        first = dcite_metadata['creator_first']
                        last = dcite_metadata['creator_last']
                        # default type of creator is []
                        if isinstance(first, list) and isinstance(last, list):
                            if len(first) == len(last):
                                names = [i + " " + j for i, j in zip(first, last)]
                                dcite_metadata['creator'] = names

                    #TODO customize related resources --> use jmes
                    if dcite_metadata['related_resources']:
                        self.logger.info('FsF-I3-01M : {0} related resource(s) extracted from {1}'.format(len(dcite_metadata['related_resources']), source_name))
                        temp_rels = []

                        for r in dcite_metadata['related_resources']:
                            temp_rels.append(dict(related_resource=r.get('relatedIdentifier'), relation_type=r.get('relationType')))
                        dcite_metadata['related_resources'] = temp_rels
                    #print(dcite_metadata)
                    # convert all values (list type) into string except 'creator','license','related_resources'
                    for key, value in dcite_metadata.items():
                        if key not in self.exclude_conversion and isinstance(value, list):
                            flat = ', '.join(map(str, value))
                            dcite_metadata[key] = flat
            except Exception as e:
                self.logger.exception('Failed to extract Datacite Json - {}'.format(e))
        return source_name, dcite_metadata
