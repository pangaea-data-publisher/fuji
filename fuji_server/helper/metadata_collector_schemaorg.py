import logging

import jmespath
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


class MetaDataCollectorSchemaOrg (MetaDataCollector):

    def __init__(self, sourcemetadata, mapping, loggerinst, ispid, pidurl):
        self.is_pid = ispid
        self.pid_url = pidurl
        super().__init__(logger=loggerinst, mapping=mapping, sourcemetadata=sourcemetadata)

    def parse_metadata(self):
        jsnld_metadata = {}
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
                ext_meta = requestHelper.content_negotiate('FsF-F2-01M')

        if ext_meta:
            self.logger.info('FsF-F2-01M : Extract metadata from {}'.format(self.source_name))
            # TODO check syntax - not ending with /, type and @type
            # TODO (important) extend mapping to detect other pids (link to related entities)?
            check_context_type = {"@context": ["http://schema.org/","http://schema.org"] , "@type": ["Dataset", "Collection"] }
            try:
                if ext_meta['@context'] in check_context_type['@context'] and ext_meta['@type'] in check_context_type[
                    "@type"]:
                    jsnld_metadata = jmespath.search(self.metadata_mapping.value, ext_meta)
                    if jsnld_metadata['creator'] is None:
                        first = jsnld_metadata['creator_first']
                        last = jsnld_metadata['creator_last']
                        if isinstance(first, list) and isinstance(last, list):
                            if len(first) == len(last):
                                names = [i + " " + j for i, j in zip(first, last)]
                                jsnld_metadata['creator'] = names
                        else:
                            jsnld_metadata['creator'] = [first + " " + last]
                    #contents = jsnld_metadata['object_content_identifier']
                   # if contents:
                    #    #if isinstance(contents, str):
                     #   for content in contents:
                      #      if content['url']:
                       #         jsnld_metadata['object_content_identifier'].append({'url':content['url']})
                #TODO: logger message for invalid context types
            except Exception as err:
                self.logger.debug('FsF-F2-01M : Failed to parse JSON-LD schema.org - {}'.format(err))
        return self.source_name, jsnld_metadata