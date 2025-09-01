# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import re

from bs4 import BeautifulSoup

from fuji_server.helper.metadata_collector import MetaDataCollector, MetadataFormats, MetadataSources
from fuji_server.helper.metadata_mapper import Mapper


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

    def parse_coverage(self, coverage, type):
        type = type.split(".")[-1]  # DCT.Period
        cov = {"type": None, "value": [], "name": None}
        coordinate_keys = ["east", "north", "northlimit", "eastlimit", "southlimit", "westlimit"]
        period_keys = ["start", "end"]
        try:
            cpts = coverage.split(";")
            for cpt in cpts:
                cvi = cpt.split("=")
                if len(cvi) == 2:
                    if type in ["Point", "Box", "Location"]:
                        cov["type"] = "spatial"
                        if cvi[0].strip() == "name":
                            cov["name"] = cvi[1]
                        if cvi[0].strip() in coordinate_keys:
                            cov["value"].append(cvi[1])
                    elif type in ["Period", "PeriodOfTime"]:
                        cov["type"] = "temporal"
                        if cvi[0].strip() == "name":
                            cov["name"] = cvi[1]
                        if cvi[0].strip() in period_keys:
                            cov["value"].append(cvi[1])
        except Exception as e:
            print("ERROR: ", e)
        return cov

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
        dc_core_base_props = [
            "contributor",
            "coverage",
            "spatial",
            "temporal",
            "creator",
            "date",
            "issued",
            "description",
            "format",
            "extent",
            "identifier",
            "language",
            "publisher",
            "relation",
            "rights",
            "source",
            "subject",
            "title",
            "type",
        ]
        source = None
        if self.source_metadata is not None:
            try:
                self.metadata_format = MetadataFormats.XHTML
                # self.logger.info('FsF-F2-01M : Trying to extract DublinCore metadata from html page')
                # get core metadat from dublin core meta tags:
                # < meta name = "DCTERMS.element" content = "Value" / >
                # meta_dc_matches = re.findall('<meta\s+([^\>]*)name=\"(DC|DCTERMS)?\.([a-z]+)\"(.*?)content=\"(.*?)\"',self.landing_html)
                # exp = '<\s*meta\s*([^\>]*)name\s*=\s*\"(DC|DCTERMS)?\.([A-Za-z]+)(\.[A-Za-z]+)?\"(.*?)content\s*=\s*\"(.*?)\"'
                meta_dc_matches = []
                self.content_type = "text/html"
                try:
                    metasoup = BeautifulSoup(self.source_metadata, "lxml")
                    meta_dc_soupresult = metasoup.findAll(
                        "meta", attrs={"name": re.compile(r"(DC|dc|DCTERMS|dcterms)\.([A-Za-z]+)")}
                    )
                    if len(meta_dc_soupresult) <= 0:
                        meta_dc_soupresult = metasoup.findAll(
                            "meta", attrs={"name": re.compile(r"(" + "|".join(dc_core_base_props) + ")")}
                        )
                    for meta_tag in meta_dc_soupresult:
                        dc_name_parts = str(meta_tag["name"]).split(".")
                        if len(dc_name_parts) == 1 and dc_name_parts[0] in dc_core_base_props:
                            dc_name_parts = ["dc", dc_name_parts[0]]
                        if len(dc_name_parts) > 1:
                            dc_t = None
                            if len(dc_name_parts) == 3:
                                dc_t = dc_name_parts[2]
                            meta_dc_matches.append(
                                [dc_name_parts[1], dc_t, meta_tag.get("content"), meta_tag.get("scheme")]
                            )
                    # meta_dc_matches = re.findall(exp, self.source_metadata)
                except Exception as e:
                    self.logger.info(f"FsF-I3-01M : Parsing error, failed to extract Dublin Core -: {e}")

                if len(meta_dc_matches) > 0:
                    self.namespaces.append("http://purl.org/dc/elements/1.1/")
                    # source = self.getEnumSourceNames().DUBLINCORE_EMBEDDED
                    source = MetadataSources.DUBLINCORE_EMBEDDED
                    dcterms = []
                    for dcitems in self.metadata_mapping.value.values():
                        if isinstance(dcitems, list):
                            for dcitem in dcitems:
                                dcterms.append(str(dcitem).lower())
                            # dcterms.extend(dcitems)
                        else:
                            dcterms.append(str(dcitems).lower())
                    for dc_meta in meta_dc_matches:
                        try:
                            # dc_meta --> ('', 'DC', 'creator', ' ', 'Hillenbrand, Claus-Dieter')
                            # key
                            k = str(dc_meta[0])  # 2
                            # type
                            t = dc_meta[1]  # 3
                            # value
                            v = dc_meta[2]  # 5
                            # ccheme
                            # s = dc_meta[3]
                            if k.lower() == "date":
                                if t == "dateAccepted":
                                    dc_core_metadata["accepted_date"] = v
                                elif t == "dateSubmitted":
                                    dc_core_metadata["submitted_date"] = v

                            # if self.isDebug:
                            #   self.logger.info('FsF-F2-01M: DublinCore metadata element, %s = %s , ' % (k, v)
                            if k.lower() in dcterms:
                                # self.logger.info('FsF-F2-01M: DublinCore metadata element, %s = %s , ' % (k, v))
                                try:
                                    elem = next(
                                        key
                                        for (key, value) in Mapper.DC_MAPPING.value.items()
                                        if k.lower() in str(value).lower()
                                    )  # fuji ref fields
                                except Exception:
                                    # nothing found so just continue
                                    pass
                                if elem in ["coverage_spatial", "coverage_temporal"]:
                                    try:
                                        coverage_info = self.parse_coverage(v, elem.split("_")[-1])
                                        v = {
                                            "name": coverage_info.get("name"),
                                            "reference": coverage_info.get("reference"),
                                        }
                                        if coverage_info.get("type") == "spatial":
                                            v["coordinates"] = coverage_info.get("value")
                                            elem = "coverage_spatial"
                                        else:
                                            elem = "coverage_temporal"
                                            v["dates"] = coverage_info.get("value")
                                        v = [v]
                                    except Exception as e:
                                        self.logger.info(
                                            f"FsF-I3-01M : Parsing error, failed to extract Dublin Core coverage info -: {e}"
                                        )
                                        pass
                                if elem == "related_resources":
                                    # dc_core_metadata['related_resources'] = []
                                    # tuple of type and relation
                                    # Mapping see: https://www.w3.org/TR/prov-dc/
                                    # qualifiers, subproperties (t):
                                    # https://www.dublincore.org/specifications/dublin-core/dcmes-qualifiers/
                                    # https://www.dublincore.org/specifications/dublin-core/dcq-html/
                                    if k in ["source", "references"]:
                                        t = "wasDerivedFrom"
                                    elif k == "relation":
                                        if t in [None, ""]:
                                            t = "isRelatedTo"
                                    else:
                                        t = k
                                    v = [{"related_resource": v, "relation_type": t}]  # must be a list of dict
                                    # v = dict(related_resource=v, relation_type=t)
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
                        except Exception as e:
                            self.logger.info(f"FsF-I3-01M : Parsing error, failed to parse Dublin Core property -: {e}")
                    if dc_core_metadata.get("related_resources"):
                        count = len([d for d in dc_core_metadata.get("related_resources") if d.get("related_resource")])
                        self.logger.info(
                            "FsF-I3-01M : number of related resource(s) extracted from Dublin Core -: {} from {}".format(
                                count, source.name
                            )
                        )
                    else:
                        self.logger.info("FsF-I3-01M : No related resource(s) found in Dublin Core metadata")
                    # process string-based file format
                    # https://www.dublincore.org/specifications/dublin-core/dcmi-dcsv/
                    """if dc_core_metadata.get('file_format_only'):
                        format_str = dc_core_metadata.get('file_format_only')
                        if isinstance(format_str, str):
                            format_str = re.split(';|,', format_str)[0].strip(
                            )  # assume first value as media type #TODO use regex to extract mimetype
                            dc_core_metadata['file_format_only'] = format_str"""
            except Exception as e:
                self.logger.exception(f"Failed to extract Dublin Core - {e}")
        return source, dc_core_metadata
