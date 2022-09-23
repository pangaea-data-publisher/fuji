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

import re
from bs4 import BeautifulSoup
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.metadata_collector import MetaDataCollector


class MetaDataCollectorDublinCore(MetaDataCollector):
    """
    A class to collect Dublin Core metadata. This class is child class of MetadataCollector.

    ...

    Methods
    --------
    parse_metadata()
        Method to parse Dublin Core metadata from the data.

    """

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
        """Parse the Dublin Core metadata from the data

        Returns
        ------
        str
            a string of source name
        dict
            a dictionary of Dublin Core metadata
        """
        dc_core_metadata = {}
        dc_core_base_props = ['contributor', 'coverage', 'creator', 'date', 'issued', 'description', 'format', 'identifier',
                              'language', 'publisher', 'relation', 'rights', 'source', 'subject', 'title', 'type']
        source = None
        if self.source_metadata is not None:
            try:
                #self.logger.info('FsF-F2-01M : Trying to extract DublinCore metadata from html page')
                # get core metadat from dublin core meta tags:
                # < meta name = "DCTERMS.element" content = "Value" / >
                # meta_dc_matches = re.findall('<meta\s+([^\>]*)name=\"(DC|DCTERMS)?\.([a-z]+)\"(.*?)content=\"(.*?)\"',self.landing_html)
                #exp = '<\s*meta\s*([^\>]*)name\s*=\s*\"(DC|DCTERMS)?\.([A-Za-z]+)(\.[A-Za-z]+)?\"(.*?)content\s*=\s*\"(.*?)\"'
                meta_dc_matches = []
                self.content_type = 'text/html'
                try:

                    metasoup = BeautifulSoup(self.source_metadata, 'lxml')
                    meta_dc_soupresult = metasoup.findAll(
                        'meta', attrs={'name': re.compile(r'(DC|dc|DCTERMS|dcterms)\.([A-Za-z]+)')})

                    if len(meta_dc_soupresult) <= 0:
                        meta_dc_soupresult = metasoup.findAll(
                            'meta', attrs={'name':re.compile(r'('+'|'.join(dc_core_base_props)+')')})
                    for meta_tag in meta_dc_soupresult:
                        dc_name_parts = str(meta_tag['name']).split('.')
                        if len(dc_name_parts) == 1 and dc_name_parts[0] in dc_core_base_props:
                            dc_name_parts = ['dc',dc_name_parts[0]]
                        if (len(dc_name_parts) > 1):
                            dc_t = None
                            if len(dc_name_parts) == 3:
                                dc_t = dc_name_parts[2]
                            meta_dc_matches.append([dc_name_parts[1], dc_t, meta_tag.get('content')])
                    #meta_dc_matches = re.findall(exp, self.source_metadata)
                except Exception as e:
                    self.logger.exception('Parsing error, failed to extract DublinCore -: {}'.format(e))
                if len(meta_dc_matches) > 0:
                    self.namespaces.append('http://purl.org/dc/elements/1.1/')
                    source = self.getEnumSourceNames().DUBLINCORE.value
                    dcterms = []
                    for dcitems in self.metadata_mapping.value.values():
                        if isinstance(dcitems, list):
                            for dcitem in dcitems:
                                dcterms.append(str(dcitem).lower())
                            #dcterms.extend(dcitems)
                        else:
                            dcterms.append(str(dcitems).lower())
                    for dc_meta in meta_dc_matches:
                        # dc_meta --> ('', 'DC', 'creator', ' ', 'Hillenbrand, Claus-Dieter')
                        #key
                        k = str(dc_meta[0])  #2
                        #type
                        t = dc_meta[1]  #3
                        #value
                        v = dc_meta[2]  #5

                        if k.lower() == 'date':
                            if t == 'dateAccepted':
                                dc_core_metadata['accepted_date'] = v
                            elif t == 'dateSubmitted':
                                dc_core_metadata['submitted_date'] = v

                        # if self.isDebug:
                        #   self.logger.info('FsF-F2-01M: DublinCore metadata element, %s = %s , ' % (k, v)
                        if k.lower() in dcterms:
                            #self.logger.info('FsF-F2-01M: DublinCore metadata element, %s = %s , ' % (k, v))
                            try:
                                elem = [key for (key, value) in Mapper.DC_MAPPING.value.items() if k.lower() in str(value).lower()
                                        ][0]  # fuji ref fields
                            except Exception as e:
                                #nothing found so just continue
                                pass
                            if elem == 'related_resources':
                                #dc_core_metadata['related_resources'] = []
                                # tuple of type and relation
                                #Mapping see: https://www.w3.org/TR/prov-dc/
                                #qualifiers, subproperties (t):
                                #https://www.dublincore.org/specifications/dublin-core/dcmes-qualifiers/
                                #https://www.dublincore.org/specifications/dublin-core/dcq-html/
                                if k in ['source', 'references']:
                                    t = 'wasDerivedFrom'
                                elif k == 'relation':
                                    if t in [None, '']:
                                        t = 'isRelatedTo'
                                else:
                                    t = k
                                v = [{'related_resource': v, 'relation_type': t}]  # must be a list of dict
                                #v = dict(related_resource=v, relation_type=t)
                            if v:
                                if elem in dc_core_metadata:
                                    if isinstance(dc_core_metadata[elem], list):
                                        if isinstance(v, list):
                                            dc_core_metadata[elem].extend(v)
                                        else:
                                            dc_core_metadata[elem].append(v)
                                    else:
                                        temp_list = []
                                        temp_list.append(dc_core_metadata[elem])
                                        temp_list.append(v)
                                        dc_core_metadata[elem] = temp_list
                                else:
                                    dc_core_metadata[elem] = v
                    if dc_core_metadata.get('related_resources'):
                        count = len([d for d in dc_core_metadata.get('related_resources') if d.get('related_resource')])
                        self.logger.info(
                            'FsF-I3-01M : number of related resource(s) extracted from DublinCore -: {0} from {1}'.
                            format(count, source))
                    else:
                        self.logger.warning('FsF-I3-01M : No related resource(s) found in DublinCore metadata')
                    # process string-based file format
                    # https://www.dublincore.org/specifications/dublin-core/dcmi-dcsv/
                    if dc_core_metadata.get('file_format_only'):
                        format_str = dc_core_metadata.get('file_format_only')
                        if isinstance(format_str, str):
                            format_str = re.split(';|,', format_str)[0].strip(
                            )  # assume first value as media type #TODO use regex to extract mimetype
                            dc_core_metadata['file_format_only'] = format_str
            except Exception as e:
                self.logger.exception('Failed to extract DublinCore - {}'.format(e))
        return source, dc_core_metadata
