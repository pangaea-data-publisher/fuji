# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import jmespath

from fuji_server.helper.metadata_collector import MetaDataCollector, MetadataSources
from fuji_server.helper.request_helper import AcceptTypes, RequestHelper


class MetaDataCollectorDatacite(MetaDataCollector):
    """
    A class to collect Datacite metadata. This class is child class of MetadataCollector.
    Several metadata are excluded from the collection, those are 'creator', 'license',
    'related_resources', and 'access_level'.

    ...

    Attributes
    ----------
    exclude_conversion : list
        List of string to store the excluded metadata
    pid_url : str
        URL of PID

    Methods
    --------
    parse_metadata()
        Method to parse Datacite metadata from the data
    """

    exclude_conversion: list[str]

    def __init__(self, mapping, pid_url=None, loggerinst=None):
        """
        Parameters
        ----------
        mapping: Mapper
            Mapper to metedata sources
        pid_url : str, optional
            URL of PID
        loggerinst : logging.logger, optional
            Logger instance
        """
        super().__init__(logger=loggerinst, mapping=mapping)
        self.pid_url = pid_url
        self.exclude_conversion = ["creator", "license", "related_resources", "access_level"]
        self.accept_type = AcceptTypes.datacite_json

    def parse_metadata(self):
        """Parse the Datacite metadata from the data

        Returns
        ------
        str
            string of source name
        list
            a list of strings of Datacite metadata exclude 'creator', 'license', 'related_resources', 'access_level'
        """
        source_name = None
        dcite_metadata = {}
        if self.pid_url:
            self.logger.info("FsF-F2-01M : Trying to retrieve datacite metadata")
            requestHelper = RequestHelper(self.pid_url, self.logger)
            requestHelper.setAcceptType(self.accept_type)
            neg_format, ext_meta = requestHelper.content_negotiate("FsF-F2-01M")
            self.metadata_format = neg_format
            self.content_type = requestHelper.content_type
            if ext_meta:
                try:
                    dcite_metadata = jmespath.search(self.metadata_mapping.value, ext_meta)
                    if dcite_metadata:
                        self.setLinkedNamespaces(str(ext_meta))
                        self.namespaces.append("http://datacite.org/schema/")
                        source_name = MetadataSources.DATACITE_JSON_NEGOTIATED
                        if dcite_metadata["creator"] is None:
                            first = dcite_metadata["creator_first"]
                            last = dcite_metadata["creator_last"]
                            # default type of creator is []
                            if isinstance(first, list) and isinstance(last, list):
                                if len(first) == len(last):
                                    names = [i + " " + j for i, j in zip(first, last)]
                                    dcite_metadata["creator"] = names

                        if dcite_metadata.get("related_resources"):
                            self.logger.info(
                                "FsF-I3-01M : {} related resource(s) extracted from -: {}".format(
                                    len(dcite_metadata["related_resources"]), source_name.name
                                )
                            )
                            temp_rels = []
                            for r in dcite_metadata["related_resources"]:
                                if r.get("scheme_uri"):
                                    self.namespaces.append(r.get("scheme_uri"))
                                filtered = {k: v for k, v in r.items() if v is not None}
                                temp_rels.append(filtered)
                            dcite_metadata["related_resources"] = temp_rels
                        else:
                            self.logger.info("FsF-I3-01M : No related resource(s) found in Datacite metadata")

                        # convert all values (list type) into string except 'creator','license','related_resources'
                        for key, value in dcite_metadata.items():
                            if key not in self.exclude_conversion and isinstance(value, list):
                                flat = ", ".join(map(str, value))
                                dcite_metadata[key] = flat
                except Exception as e:
                    self.logger.warning(f"FsF-F2-01M : Failed to extract Datacite JSON -: {e}")
                    # self.logger.exception('Failed to extract Datacite JSON -: {}'.format(e))
        else:
            self.logger.warning("FsF-F2-01M : Skipped Datacite metadata retrieval, no PID URL detected")

        return source_name, dcite_metadata
