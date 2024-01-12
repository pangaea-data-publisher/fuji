# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import jmespath

from fuji_server.helper.metadata_collector import MetaDataCollector, MetadataFormats
from fuji_server.helper.preprocessor import Preprocessor


class MetaDataCollectorMicroData(MetaDataCollector):
    """
    A class to collect the Microdata metadata from the data. This class is child class of MetadataCollector.

    ...

    Attributes
    ----------
    source_name : str
        Source name of metadata

    Methods
    --------
    parse_metadata()
        Method to parse the Microdata metadata from the data.
    """

    source_name = None
    SCHEMA_ORG_CREATIVEWORKS = Preprocessor.get_schema_org_creativeworks()

    def __init__(self, sourcemetadata, mapping, loggerinst):
        """
        Parameters
        ----------
        sourcemetadata : str
            Source of metadata
        mapping : Mapper
            Mapper to metedata sources
        loggerinst : logging.Logger
            Logger instance
        target_url : str
            Target URL
        """
        super().__init__(logger=loggerinst, mapping=mapping, sourcemetadata=sourcemetadata)

    def parse_metadata(self):
        """Parse the metadata from Microdata

        Returns
        ------
        str
            a string of source name
        dict
            a dictionary of Microdata metadata
        """
        micro_metadata = {}
        ext_meta = None
        self.content_type = "text/html"
        self.metadata_format = MetadataFormats.MICRODATA
        if self.source_metadata:
            # print(self.source_metadata)
            if len(self.source_metadata) > 1:
                try:
                    for sm in self.source_metadata:
                        if str(sm.get("type").split("/")[-1]).lower() in self.SCHEMA_ORG_CREATIVEWORKS:
                            ext_meta = sm
                except:
                    pass
            self.source_name = self.getEnumSourceNames().MICRODATA_EMBEDDED
            if not ext_meta:
                ext_meta = self.source_metadata[0]

        if ext_meta is not None:
            self.logger.info(f"FsF-F2-01M : Trying to extract Microdata metadata from -: {self.source_name}")
            # TODO check syntax - not ending with /, type and @type
            # TODO (important) extend mapping to detect other pids (link to related entities)?
            # TODO replace check_context_type list context comparison by regex
            try:
                # if ext_meta['@context'] in check_context_type['@context'] and ext_meta['@type'] in check_context_type["@type"]:
                if str(ext_meta.get("type")).find("schema.org") > -1:
                    micro_metadata = jmespath.search(self.metadata_mapping.value, ext_meta)
                    self.namespaces.append("http://schema.org/")
                else:
                    self.logger.info("FsF-F2-01M : Failed to parse non schema.org type Microdata")
            except Exception as err:
                # print(err.with_traceback())
                self.logger.info(f"FsF-F2-01M : Failed to parse Microdata -: {err}")
        else:
            self.logger.info("FsF-F2-01M : Could not identify Microdata metadata")

        return self.source_name, micro_metadata
