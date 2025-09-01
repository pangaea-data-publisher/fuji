# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import re

import idutils
import lxml

from fuji_server.helper.metadata_collector import MetaDataCollector, MetadataFormats, MetadataOfferingMethods
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.request_helper import AcceptTypes, RequestHelper


class MetaDataCollectorXML(MetaDataCollector):
    """
    A class to collect the  XML metadata given the data. This class is child class of MetadataCollector.

    ...

    Attributes
    ----------
    target_url : str
        Target URL of the metadata
    link_type : str
        Link type of XML

    Methods
    --------
    parse_metadata()
        Method to parse the  XML metadata given the data
    get_mapped_xml_metadata(tree, mapping)
        Get mapped xml metadata

    """

    def __init__(self, loggerinst, target_url=None, link_type="linked", pref_mime_type=None):
        """
        Parameters
        ----------
        mapping : Mapper
            Mapper to metedata sources
        loggerinst : logging.Logger
            Logger instance
        link_type : str, optional
            Link Type, from MetadataOfferigMethods enum
        pref_mime_type : str, optional
            Preferred mime type, e.g. specific XML format
        """
        self.target_url = target_url
        self.link_type = link_type
        self.pref_mime_type = pref_mime_type
        self.is_xml = False
        super().__init__(logger=loggerinst)

    def getAllURIs(self, metatree):
        founduris = []
        try:
            # all text element values
            elr = metatree.xpath("//text()")
            for el in elr:
                if str(el).strip():
                    if el not in founduris:
                        if idutils.is_url(el) or idutils.is_urn(el):
                            founduris.append(str(el))
            # all attribute values
            alr = metatree.xpath("//@*")
            for al in alr:
                if al not in founduris:
                    if idutils.is_url(al) or idutils.is_urn(al):
                        founduris.append(str(al))
            founduris = list(set(founduris))
            # xpath
            # //text()
            # //@*
        except Exception as e:
            print("getAllURIs XML error: " + str(e))
        return founduris

    def parse_metadata(self):
        """Parse the XML metadata from the data.

        Returns
        ------
        str
            a string of source name
        dict
            a dictionary of XML metadata
        """
        xml_metadata = None
        xml_mapping = None
        metatree = None
        envelope_metadata = {}
        self.content_type = "application/xml"

        XSI = "http://www.w3.org/2001/XMLSchema-instance"

        if self.link_type == MetadataOfferingMethods.TYPED_LINKS:
            source_name = self.getEnumSourceNames().XML_TYPED_LINKS
        # elif self.link_type == 'guessed':
        #    source_name = self.getEnumSourceNames().XML_GUESSED
        elif self.link_type == MetadataOfferingMethods.CONTENT_NEGOTIATION:
            source_name = self.getEnumSourceNames().XML_NEGOTIATED
        else:
            source_name = self.getEnumSourceNames().XML_TYPED_LINKS
        requestHelper = RequestHelper(self.target_url, self.logger)
        requestHelper.setAcceptType(AcceptTypes.xml)
        requestHelper.setAuthToken(self.auth_token, self.auth_token_type)
        if self.pref_mime_type:
            requestHelper.addAcceptType(self.pref_mime_type)
        # self.logger.info('FsF-F2-01M : Sending request to access metadata from -: {}'.format(self.target_url))
        neg_format, xml_response = requestHelper.content_negotiate("FsF-F2-01M")
        self.metadata_format = neg_format
        if requestHelper.response_content is not None:
            self.content_type = requestHelper.content_type
            self.logger.info(f"FsF-F2-01M : Trying to extract/parse XML metadata from URL -: {self.target_url}")
            # dom = lxml.html.fromstring(self.landing_html.encode('utf8'))
            if neg_format != MetadataFormats.XML:
                # if neg_source != 'xml':
                self.logger.info("FsF-F2-01M : Expected XML but content negotiation responded -: " + str(neg_format))
            else:
                self.is_xml = True
                try:
                    parser = lxml.etree.XMLParser(strip_cdata=False, recover=True)
                    tree = lxml.etree.XML(xml_response, parser)
                    root_element = tree.tag
                    if root_element.endswith("}OAI-PMH"):
                        self.logger.info(
                            "FsF-F2-01M : Found OAI-PMH type XML envelope, unpacking 'metadata' element for further processing"
                        )
                        metatree = tree.find(".//{*}metadata/*")
                    elif root_element.endswith("}mets"):
                        self.logger.info(
                            "FsF-F2-01M : Found METS type XML envelope, unpacking all 'xmlData' elements for further processing"
                        )
                        envelope_metadata = self.get_mapped_xml_metadata(tree, Mapper.XML_MAPPING_METS.value)
                        metatree = tree.find(".//{*}dmdSec/{*}mdWrap/{*}xmlData/*")
                    elif root_element.endswith("}GetRecordsResponse"):
                        self.logger.info(
                            "FsF-F2-01M : Found OGC CSW GetRecords type XML envelope, unpacking 'SearchResults' element for further processing"
                        )
                        metatree = tree.find(".//{*}SearchResults/*")
                    elif root_element.endswith("}GetRecordByIdResponse"):
                        self.logger.info(
                            "FsF-F2-01M : Found OGC CSW GetRecordByIdResponse type XML envelope, unpacking metadata element for further processing"
                        )
                        metatree = tree.find(".//*")
                    elif root_element.endswith("}DIDL"):
                        self.logger.info(
                            "FsF-F2-01M : Found DIDL (MPEG21) type XML envelope, unpacking metadata element for further processing"
                        )
                        metatree = tree.find(".//{*}Item/{*}Component/{*}Resource/*")
                    else:
                        metatree = tree
                except Exception as e:
                    self.logger.info("FsF-F2-01M : XML parsing failed -: " + str(e))
                    print("FsF-F2-01M : XML parsing failed -: " + str(e))
                if metatree is not None:
                    # self.setURIValues(metatree)
                    # print(list(set(self.getURIValues())))

                    self.logger.info(
                        "FsF-F2-01M : Found some XML properties, trying to identify (domain) specific format to parse"
                    )
                    root_namespace = None
                    nsmatch = re.match(r"^\{(.+)\}(.+)$", metatree.tag)
                    schema_locations = set(metatree.xpath("//*/@xsi:schemaLocation", namespaces={"xsi": XSI}))
                    for schema_location in schema_locations:
                        self.namespaces.extend(re.split(r"\s", re.sub(r"\s+", r" ", schema_location)))
                        # self.namespaces = re.split('\s', schema_location)
                    element_namespaces = set(metatree.xpath("//namespace::*"))
                    for el_ns in element_namespaces:
                        if len(el_ns) == 2:
                            if el_ns[1] not in self.namespaces:
                                self.namespaces.append(el_ns[1])
                    if nsmatch:
                        root_namespace = nsmatch[1]
                        root_element = nsmatch[2]
                        # put the root namespace at the start f list
                        self.namespaces.insert(0, root_namespace)
                    if root_element == "codeBook":
                        xml_mapping = Mapper.XML_MAPPING_DDI_CODEBOOK.value
                        self.logger.info("FsF-F2-01M : Identified DDI codeBook XML based on root tag")
                        self.namespaces.append("ddi:codebook:2_5")
                    elif root_element in ["StudyUnit", "DDIInstance"]:
                        xml_mapping = Mapper.XML_MAPPING_DDI_STUDYUNIT.value
                        self.logger.info("FsF-F2-01M : Identified DDI StudyUnit XML based on root tag")
                        self.namespaces.append("ddi:studyunit:3_2")
                    elif root_element == "CMD":
                        xml_mapping = Mapper.XML_MAPPING_CMD.value
                        self.logger.info("FsF-F2-01M : Identified Clarin CMDI XML based on root tag")
                        self.namespaces.append("http://www.clarin.eu/cmd/")
                    elif root_element == "DIF":
                        xml_mapping = Mapper.XML_MAPPING_DIF.value
                        self.logger.info(
                            "FsF-F2-01M : Identified Directory Interchange Format (DIF) XML based on root tag"
                        )
                        self.namespaces.append("http://gcmd.gsfc.nasa.gov/Aboutus/xml/dif/")
                    elif root_element == "dc" or any(
                        "http://dublincore.org/schemas/xmls/" in s for s in self.namespaces
                    ):
                        xml_mapping = Mapper.XML_MAPPING_DUBLIN_CORE.value
                        self.logger.info("FsF-F2-01M : Identified Dublin Core XML based on root tag or namespace")
                        self.namespaces.append("http://purl.org/dc/elements/1.1/")
                    elif root_element == "mods":
                        xml_mapping = Mapper.XML_MAPPING_MODS.value
                        self.logger.info("FsF-F2-01M : Identified MODS XML based on root tag")
                        self.namespaces.append("http://www.loc.gov/mods/")
                    elif root_element == "eml":
                        xml_mapping = Mapper.XML_MAPPING_EML.value
                        self.logger.info("FsF-F2-01M : Identified EML XML based on root tag")
                        self.namespaces.append("eml://ecoinformatics.org/eml-2.0.0")
                    elif root_element in ["MD_Metadata", "MI_Metadata"]:
                        xml_mapping = Mapper.XML_MAPPING_GCMD_ISO.value
                        self.logger.info("FsF-F2-01M : Identified ISO 19115 XML based on root tag")
                        self.namespaces.append("http://www.isotc211.org/2005/gmd")
                    elif root_element == "rss":
                        self.logger.info("FsF-F2-01M : Identified RSS/GEORSS XML based on root tag")
                        self.namespaces.append("http://www.georss.org/georss/")
                    elif root_element == "ead":
                        xml_mapping = Mapper.XML_MAPPING_EAD.value
                        self.logger.info("FsF-F2-01M : Identified EAD XML based on root tag")
                        self.namespaces.append("http://ead3.archivists.org/schema/")
                    elif root_element == "TEI":
                        xml_mapping = Mapper.XML_MAPPING_TEI.value
                        self.logger.info("FsF-F2-01M : Identified TEI XML based on root tag")
                        self.namespaces.append("http://www.tei-c.org/ns/1.0")
                    elif root_namespace:
                        if "datacite.org/schema" in root_namespace:
                            xml_mapping = Mapper.XML_MAPPING_DATACITE.value
                            self.logger.info("FsF-F2-01M : Identified DataCite XML based on namespace")
                    # print('XML Details: ',(self.target_url,root_namespace, root_element, type(root_element),xml_mapping))
                    linkeduris = self.getAllURIs(metatree)
                    self.setLinkedNamespaces(linkeduris)
                    if xml_mapping is None:
                        self.logger.info("FsF-F2-01M : Could not identify (domain) specific XML format to parse")
                else:
                    self.logger.info(
                        "FsF-F2-01M : Could not find XML properties, could not identify specific XML format to parse"
                    )
        if xml_mapping and metatree is not None:
            xml_metadata = self.get_mapped_xml_metadata(metatree, xml_mapping)

        if envelope_metadata and xml_metadata:
            for envelope_key, envelope_values in envelope_metadata.items():
                if envelope_key not in xml_metadata:
                    xml_metadata[envelope_key] = envelope_values

        # delete empty properties
        if xml_metadata:
            xml_metadata = {k: v for k, v in xml_metadata.items() if v}

        if xml_metadata:
            if requestHelper.checked_content_hash:
                if requestHelper.checked_content.get(requestHelper.checked_content_hash):
                    requestHelper.checked_content.get(requestHelper.checked_content_hash)["checked"] = True
            self.logger.info("FsF-F2-01M : Found some metadata in XML -: " + (str(xml_metadata.keys())))
        else:
            self.logger.info("FsF-F2-01M : Could not identify metadata properties in XML")
        return source_name, xml_metadata

    def get_tree_property_list(self, propcontent):
        res = []
        if isinstance(propcontent, list):
            if len(propcontent) == 1:
                if propcontent[0].get("attribute"):
                    res = propcontent[0].get("tree").attrib.get(propcontent[0].get("attribute"))
                elif len(propcontent[0].get("tree")) == 0:
                    res = propcontent[0].get("tree").text
                else:
                    res = lxml.etree.tostring(propcontent[0].get("tree"), method="text", encoding="unicode")
                    res = re.sub(r"\s+", " ", res)
                    res = res.strip()
                res = [res]
            else:
                for propelem in propcontent:
                    if propelem.get("attribute"):
                        res.append(propelem.get("tree").attrib.get(propelem.get("attribute")))
                    elif len(propelem.get("tree")) == 0:
                        res.append(propelem.get("tree").text)
                    else:
                        resprop = lxml.etree.tostring(propelem.get("tree"), method="text", encoding="unicode")
                        resprop = re.sub(r"\s+", " ", resprop)
                        resprop = resprop.strip()
                        res.append(resprop)
        return res

    def path_query(self, mappath, tree):
        pathdef = mappath.split("@@")
        attribute = None
        if len(pathdef) > 1:
            attribute = pathdef[1]
            if ":" in attribute:
                if attribute.split(":")[0] == "xlink":
                    attribute = "{http://www.w3.org/1999/xlink}" + attribute.split(":")[1]
                elif attribute.split(":")[0] == "xml":
                    attribute = "{http://www.w3.org/XML/1998/namespace}" + attribute.split(":")[1]
        try:
            subtrees = tree.findall(pathdef[0])
        except Exception as e:
            subtrees = []
            print("XML XPATH error ", str(e), str(pathdef[0]))
        return subtrees, attribute

    def get_mapped_xml_metadata(self, tree, mapping):
        """Get the mapped XML metadata.

        Parameters
        ----------
        tree
            XML Tree
        mapping
            Mapping object

        Returns
        ------

        dict
            a dictionary of mapped XML metadata
        """
        res = dict()
        # make sure related_resources are not listed in the mapping dict instead related_resource_Reltype has to be used
        res["related_resources"] = []
        for prop in mapping:
            res[prop] = []
            if isinstance(mapping.get(prop).get("path"), list):
                pathlist = mapping.get(prop).get("path")
            else:
                pathlist = [mapping.get(prop).get("path")]

            propcontent = []
            path_no = 0
            # in case a fixed value is given in mapping
            if mapping.get(prop).get("value"):
                res[prop] = [mapping.get(prop).get("value")]
            # otherwise as xpath is checked
            else:
                for mappath in pathlist:
                    subtrees, attribute = self.path_query(mappath, tree)
                    for subtree in subtrees:
                        if mapping.get(prop).get("subpath"):
                            subpathdict = mapping.get(prop).get("subpath")
                            if isinstance(subpathdict, list):
                                if len(subpathdict) > path_no:
                                    subpathdict = subpathdict[path_no]
                                else:
                                    subpathdict = subpathdict[0]
                            else:
                                subpathdict = subpathdict
                            for subprop, subpath in subpathdict.items():
                                if not res.get(prop + "_" + subprop):
                                    res[prop + "_" + subprop] = []
                                subsubtrees, subattribute = self.path_query(subpath, subtree)
                                if not subsubtrees:
                                    subsubtrees = [lxml.etree.Element("none")]
                                    subattribute = None
                                # print(prop+'_'+subprop,subsubtrees[0], ' -#- ',lxml.etree.tostring(subsubtrees[0], method="text", encoding="unicode"),' -#- ', subattribute)
                                subpropcontent = [{"tree": subsubtrees[0], "attribute": subattribute}]
                                if subpropcontent:
                                    # print('SUBPROP: ',subprop, self.get_tree_property_list(subpropcontent))
                                    res[prop + "_" + subprop].extend(self.get_tree_property_list(subpropcontent))
                        else:
                            propcontent.append({"tree": subtree, "attribute": attribute})
                        if propcontent:
                            res[prop] = self.get_tree_property_list(propcontent)
                    path_no += 1

        # related resources
        for kres, vres in res.items():
            if vres:
                if kres.startswith("related_resource") and "related_resource_type" not in kres:
                    if isinstance(vres, str):
                        vres = [vres]
                    reltype = kres[17:]
                    if not reltype:
                        reltype = "related"
                    ri = 0
                    for relres in vres:
                        if relres:
                            if res.get("related_resource_type"):
                                if ri < len(res["related_resource_type"]):
                                    reltype = res["related_resource_type"][ri]
                            relres = re.sub(r"[\n\t]*", "", str(relres)).strip()
                        if relres and reltype:
                            res["related_resources"].append({"related_resource": relres, "resource_type": reltype})
                        ri += 1
        # object_content_identifiers
        if res.get("object_content_identifier_url"):
            res["object_content_identifier"] = []
            if not isinstance(res["object_content_identifier_url"], list):
                res["object_content_identifier_url"] = [res["object_content_identifier_url"]]
            ci = 0
            for content_url in res["object_content_identifier_url"]:
                content_size = None
                content_type = None
                content_service = None
                if res.get("object_content_identifier_size"):
                    if ci < len(res["object_content_identifier_size"]):
                        content_size = res["object_content_identifier_size"][ci]
                if res.get("object_content_identifier_type"):
                    if ci < len(res["object_content_identifier_type"]):
                        content_type = res["object_content_identifier_type"][ci]
                if res.get("object_content_identifier_service"):
                    if ci < len(res["object_content_identifier_service"]):
                        if "WWW:LINK" not in str(
                            res["object_content_identifier_service"][ci]
                        ) and "www.w3.org/TR/xlink" not in str(res["object_content_identifier_service"][ci]):
                            content_service = res["object_content_identifier_service"][ci]
                res["object_content_identifier"].append(
                    {"url": content_url, "size": content_size, "type": content_type, "service": content_service}
                )
                ci += 1
            res.pop("object_content_identifier_type", None)
            res.pop("object_content_identifier_size", None)
            res.pop("object_content_identifier_url", None)
            res.pop("object_content_identifier_service", None)
        if res.get("coverage_temporal_dates") or res.get("coverage_temporal_names"):
            res["coverage_temporal"] = []
            if not isinstance(res["coverage_temporal_dates"], list):
                res["coverage_temporal_dates"] = [res["coverage_temporal_dates"]]
            ci = 0
            for temporal_info in res["coverage_temporal_dates"] or res.get("coverage_temporal_names"):
                temporal_dates = None
                temporal_name = None
            if res.get("coverage_temporal_dates"):
                if ci < len(res["coverage_temporal_dates"]):
                    temporal_dates = res["coverage_temporal_dates"][ci]
            if res.get("coverage_temporal_name"):
                if ci < len(res["coverage_temporal_name"]):
                    temporal_name = res["coverage_temporal_name"][ci]
            res["coverage_temporal"].append({"dates": temporal_dates, "name": temporal_name})
            ci += 1
        res.pop("coverage_temporal_dates", None)
        res.pop("coverage_temporal_name", None)
        if res.get("coverage_spatial_coordinates") or res.get("coverage_spatial_names"):
            res["coverage_spatial"] = []
            if not isinstance(res["coverage_spatial_coordinates"], list):
                res["coverage_spatial_coordinates"] = [res["coverage_spatial_coordinates"]]
            ci = 0
            for spatial_info in res["coverage_spatial_coordinates"] or res.get("coverage_spatial_names"):
                spatial_coordinates = None
                spatial_name = None
                if res.get("coverage_spatial_coordinates"):
                    if ci < len(res["coverage_spatial_coordinates"]):
                        spatial_coordinates = res["coverage_spatial_coordinates"][ci]
                if res.get("coverage_spatial_name"):
                    if ci < len(res["coverage_spatial_name"]):
                        spatial_name = res["coverage_spatial_name"][ci]
                res["coverage_spatial"].append(
                    {"coordinates": str(spatial_coordinates).split(" "), "name": spatial_name}
                )
                ci += 1
            res.pop("coverage_spatial_coordinates", None)
            res.pop("coverage_spatial_name", None)

        return res
