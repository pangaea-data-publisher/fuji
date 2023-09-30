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

from fuji_server.helper.metadata_collector import MetaDataCollector, MetadataFormats
from fuji_server.helper.metadata_mapper import Mapper


class MetaDataCollectorHighwireEprints(MetaDataCollector):
    """
    A class to collect Highwire and eprints metadata. This class is child class of MetadataCollector.

    ...

    Methods
    --------
    parse_metadata()
        Method to parse Dublin Core metadata from the data.

    """

    def __init__(self, sourcemetadata, loggerinst):
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
        super().__init__(logger=loggerinst, sourcemetadata=sourcemetadata)

    def parse_metadata(self):
        """Parse the Dublin Core metadata from the data

        Returns
        ------
        str
            a string of source name
        dict
            a dictionary of Highwire or eprints metadata
        """
        hw_core_metadata = {}
        source = self.getEnumSourceNames().HIGHWIRE_EPRINTS_EMBEDDED
        if self.source_metadata is not None:
            self.metadata_format = MetadataFormats.HTML
            self.content_type = "text/html"
            metasoup = BeautifulSoup(self.source_metadata, "lxml")
            meta_hw_soupresult = metasoup.findAll(
                "meta", attrs={"name": re.compile(r"(eprints\.|citation_)([A-Z_a-z]+)")}
            )
            flipped_hw = Mapper.flip_dict(Mapper.HIGHWIRE_MAPPING.value)
            flipped_hw.update(flipped_eprints=Mapper.flip_dict(Mapper.EPRINTS_MAPPING.value))
            for meta_tag in meta_hw_soupresult:
                hw_name_parts = str(meta_tag["name"]).split(".")
                if len(hw_name_parts) == 1:
                    elem_name = hw_name_parts[0]
                    if not "https://www.highwirepress.com/terms/" not in self.namespaces:
                        self.namespaces.append("https://www.highwirepress.com/terms/")
                elif len(hw_name_parts) == 2:
                    elem_name = hw_name_parts[1]
                    if "http://purl.org/eprint/terms/" not in self.namespaces:
                        self.namespaces.append("http://purl.org/eprint/terms/")
                else:
                    elem_name = None
                if elem_name in flipped_hw:
                    value = None
                    elem = flipped_hw.get(elem_name)
                    if isinstance(elem, tuple):
                        try:
                            value = elem[1]
                            elem = elem[0]
                        except:
                            elem = elem[0]
                            pass
                    if not value:
                        value = meta_tag.get("content")
                    if elem == "related_resources":
                        value = {"related_resource": value, "relation_type": "isRelatedTo"}
                    if not hw_core_metadata.get(elem):
                        if elem == "related_resources":
                            hw_core_metadata[elem] = [value]
                        else:
                            hw_core_metadata[elem] = value
                    else:
                        if isinstance(hw_core_metadata.get(elem), list):
                            hw_core_metadata[elem].append(value)
                        else:
                            hw_core_metadata[elem] = [hw_core_metadata[elem]].append(value)

        return source, hw_core_metadata
