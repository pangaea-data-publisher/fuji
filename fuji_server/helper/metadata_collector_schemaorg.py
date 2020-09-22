import logging

import jmespath
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


class MetaDataCollectorSchemaOrg (MetaDataCollector):
    source_name=None
    def __init__(self, sourcemetadata, mapping, loggerinst, ispid, pidurl):
        self.is_pid = ispid
        self.pid_url = pidurl
        super().__init__(logger=loggerinst, mapping=mapping, sourcemetadata=sourcemetadata)

    def parse_metadata(self):
        jsnld_metadata = {}
        ext_meta=None
        if self.source_metadata:
            self.source_name = self.getEnumSourceNames().SCHEMAORG_EMBED.value
            ext_meta = self.source_metadata[0]
        else:
            if self.is_pid:
                self.source_name = self.getEnumSourceNames().SCHEMAORG_NEGOTIATE.value
                # TODO (IMPORTANT) PID agency may support Schema.org in JSON-LD
                # TODO (IMPORTANT) validate schema.org
                # fallback, request (doi) metadata specified in schema.org JSON-LD
                requestHelper: RequestHelper = RequestHelper(self.pid_url, self.logger)
                requestHelper.setAcceptType(AcceptTypes.schemaorg)
                neg_source,ext_meta = requestHelper.content_negotiate('FsF-F2-01M')

        if ext_meta is not None:
            self.logger.info('FsF-F2-01M : Extract metadata from {}'.format(self.source_name))
            # TODO check syntax - not ending with /, type and @type
            # TODO (important) extend mapping to detect other pids (link to related entities)?
            # TODO replace check_context_type list context comparison by regex
            check_context_type =  ["Dataset", "Collection"]
            try:
                #if ext_meta['@context'] in check_context_type['@context'] and ext_meta['@type'] in check_context_type["@type"]:
                if str(ext_meta['@context']).find('://schema.org') > -1:
                    if ext_meta['@type'] in check_context_type:
                        self.namespaces.append('http://schema.org/')
                        jsnld_metadata = jmespath.search(self.metadata_mapping.value, ext_meta)
                        # TODO all properties with null values extracted through jmespath should be excluded
                        if jsnld_metadata.get('creator') is None:
                            #TODO: handle None values for first and last name
                            first = jsnld_metadata.get('creator_first')
                            last = jsnld_metadata.get('creator_last')
                            if isinstance(first, list) and isinstance(last, list):
                                if len(first) == len(last):
                                    names = [str(i) + " " + str(j) for i, j in zip(first, last)]
                                    jsnld_metadata['creator'] = names
                            else:
                                jsnld_metadata['creator'] = [str(first) + " " + str(last)]

                        if jsnld_metadata.get('license'):
                            if isinstance(jsnld_metadata.get('license'), list):
                                #self.logger.info('FsF-R1.1-01M : Non-string license metadata is specified - {0}'.format(jsnld_metadata.get('license')))
                                jsnld_metadata['license'] = jsnld_metadata.get('license')[0]

                        # filter out None values of related_resources
                        if jsnld_metadata.get('related_resources'):
                            relateds =  [d for d in jsnld_metadata['related_resources'] if d['related_resource'] is not None]
                            if relateds:
                                jsnld_metadata['related_resources'] = relateds
                                self.logger.info('FsF-I3-01M : {0} related resource(s) extracted from {1}'.format(len(jsnld_metadata['related_resources']), self.source_name))
                            else:
                                del jsnld_metadata['related_resources']
                                self.logger.info('FsF-I3-01M : No related resource(s) found in Schema.org metadata')

                        # TODO quick-fix, expand mapping expression instead
                        if jsnld_metadata.get('object_size'):
                            jsnld_metadata['object_size'] = str(jsnld_metadata['object_size'].get('value')) + ' '+ jsnld_metadata['object_size'].get('unitText')

                    else:
                        self.logger.info('FsF-F2-01M : Found JSON-LD schema.org but record is not of type "Dataset"')
                else:
                    self.logger.info('FsF-F2-01M : Found JSON-LD but seems not to be a schema.org object')
            except Exception as err:
                #print(err.with_traceback())
                self.logger.info('FsF-F2-01M : Failed to parse JSON-LD schema.org - {}'.format(err))
        else:
            self.logger.info('FsF-F2-01M : Could not identify JSON-LD schema.org metadata')

        return self.source_name, jsnld_metadata