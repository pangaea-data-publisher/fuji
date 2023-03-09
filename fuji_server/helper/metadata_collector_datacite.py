# -*- coding: utf-8 -*-
# MIT License
#
# Copyright (c) 2020 PANGAEA (https://www.pangaea.de/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import List
import jmespath
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes


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

    exclude_conversion: List[str]

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
        self.exclude_conversion = ['creator', 'license', 'related_resources', 'access_level']
        self.accept_type = AcceptTypes.datacite_json

    def parse_metadata(self):
        """ Parse the Datacite metadata from the data

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
            self.logger.info('FsF-F2-01M : Trying to retrieve datacite metadata')
            requestHelper = RequestHelper(self.pid_url, self.logger)
            requestHelper.setAcceptType(self.accept_type)
            neg_source, ext_meta = requestHelper.content_negotiate('FsF-F2-01M')
            self.content_type = requestHelper.content_type
            if ext_meta:
                try:
                    dcite_metadata = jmespath.search(self.metadata_mapping.value, ext_meta)
                    if dcite_metadata:
                        self.setLinkedNamespaces(str(ext_meta))
                        self.namespaces.append('http://datacite.org/schema/')
                        source_name = self.getEnumSourceNames().DATACITE_JSON_NEGOTIATED.value
                        if dcite_metadata['creator'] is None:
                            first = dcite_metadata['creator_first']
                            last = dcite_metadata['creator_last']
                            # default type of creator is []
                            if isinstance(first, list) and isinstance(last, list):
                                if len(first) == len(last):
                                    names = [i + ' ' + j for i, j in zip(first, last)]
                                    dcite_metadata['creator'] = names

                        if dcite_metadata.get('related_resources'):
                            self.logger.info('FsF-I3-01M : {0} related resource(s) extracted from -: {1}'.format(
                                len(dcite_metadata['related_resources']), source_name))
                            temp_rels = []

                            for r in dcite_metadata['related_resources']:
                                if r.get('scheme_uri'):
                                    self.namespaces.append(r.get('scheme_uri'))
                                filtered = {k: v for k, v in r.items() if v is not None}
                                temp_rels.append(filtered)
                            dcite_metadata['related_resources'] = temp_rels
                        else:
                            self.logger.info('FsF-I3-01M : No related resource(s) found in Datacite metadata')

                        # convert all values (list type) into string except 'creator','license','related_resources'
                        for key, value in dcite_metadata.items():
                            if key not in self.exclude_conversion and isinstance(value, list):
                                flat = ', '.join(map(str, value))
                                dcite_metadata[key] = flat
                except Exception as e:
                    self.logger.exception('Failed to extract Datacite Json -: {}'.format(e))
        else:
            self.logger.warning('FsF-F2-01M : Skipped Datacite metadata retrieval, no PID URL detected')

        return source_name, dcite_metadata
