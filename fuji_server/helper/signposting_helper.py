# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import logging
import re
from urllib.parse import urljoin, urlparse

import lxml

from fuji_server.helper.compatibility_helper import CompatibiltyHelper
from fuji_server.helper.metadata_collector import MetadataOfferingMethods
from fuji_server.helper.request_helper import AcceptTypes, RequestHelper

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SignpostingHelper:
    signposting_relation_types = [
        "describedby",
        "item",
        "license",
        "type",
        "collection",
        "author",
        "linkset",
        "cite-as",
        "api-catalog",
        "service-doc",
        "service-desc",
        "service-meta",
    ]

    def __init__(self, metric_version=0):
        self.ch = CompatibiltyHelper(metric_version=metric_version)
        self.typed_links = []  # all typed links
        self.url = None
        self.headers = {}
        self.html = None
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger()

    def set_all_typed_and_signposting_links(self, url, pid, html, headers):
        self.url = url
        self.html = html
        self.headers = headers
        # set all typed/signpostinglinks
        self.set_typed_content_links()
        self.set_signposting_header_links()
        self.set_signposting_linkset_links()

    def set_signposting_header_links(self):
        header_link_string = self.headers.get("Link")
        header_links = []
        if header_link_string is not None:
            header_links = self.parse_signposting_http_link_format(header_link_string, origin="header")
        if header_links:
            self.typed_links.extend(header_links)
            self.logger.info(
                self.ch.get_metric("pid")
                + " : Found signposting links in response header of landingpage -: "
                + str(len(header_links))
            )

    def set_typed_content_links(self):
        try:
            html = self.html.decode()
        except (UnicodeDecodeError, AttributeError):
            html = self.html
            pass
        if isinstance(html, str):
            if html:
                try:
                    dom = lxml.html.fromstring(html.encode("utf8"))
                    links = dom.xpath("/*/head/link")
                    for link in links:
                        source = MetadataOfferingMethods.TYPED_LINKS
                        href = link.attrib.get("href")
                        rel = link.attrib.get("rel")
                        type = link.attrib.get("type")
                        profile = link.attrib.get("profile")
                        type = str(type).strip()
                        # handle relative paths
                        linkparts = urlparse(href)
                        if linkparts.scheme == "":
                            href = urljoin(self.url, href)
                        if linkparts.path.endswith(".xml"):
                            if type not in ["application/xml", "text/xml"] and not type.endswith("+xml"):
                                type += "+xml"
                        # signposting links
                        # https://www.w3.org/2001/sw/RDFCore/20031212-rdfinhtml/ recommends: link rel="meta" as well as "alternate meta"
                        if rel in [
                            "meta",
                            "alternate meta",
                            "metadata",
                            "collection",
                            "author",
                            "describes",
                            "item",
                            "type",
                            "search",
                            "alternate",
                            "describedby",
                            "cite-as",
                            "linkset",
                            "license",
                            "api-catalog",
                        ]:
                            if rel in self.signposting_relation_types:
                                source = MetadataOfferingMethods.SIGNPOSTING.name
                            self.typed_links.append(
                                {
                                    "url": href,
                                    "type": type,
                                    "rel": rel,
                                    "profile": profile,
                                    "source": source,
                                    "origin": "content",
                                }
                            )
                except:
                    self.logger.info(
                        self.ch.get_metric("metadata_properties") + " : Typed links identification failed -:"
                    )
            else:
                self.logger.info(
                    self.ch.get_metric("metadata_properties")
                    + " : Expected HTML to check for typed links but received empty string "
                )

    def parse_signposting_http_link_format(self, signposting_link_format_text, origin):
        found_signposting_links = []
        for preparsed_link in signposting_link_format_text.split(","):
            found_link = None
            found_type, type_match, anchor_match = None, None, None
            found_rel, rel_match = None, None
            found_formats, formats_match = None, None
            parsed_link = preparsed_link.strip().split(";")
            found_link = parsed_link[0].strip()
            for link_prop in parsed_link[1:]:
                link_prop = str(link_prop).strip()
                if link_prop.startswith("anchor"):
                    anchor_match = re.search(r'anchor\s*=\s*\"?([^,;"]+)\"?', link_prop)
                if link_prop.startswith("rel"):
                    rel_match = re.search(r'rel\s*=\s*\"?([^,;"]+)\"?', link_prop)
                elif link_prop.startswith("type"):
                    type_match = re.search(r'type\s*=\s*\"?([^,;"]+)\"?', link_prop)
                elif link_prop.startswith("profile"):
                    formats_match = re.search(r'profile\s*=\s*\"?([^,;"]+)\"?', link_prop)
            if type_match:
                found_type = type_match[1]
            if rel_match:
                found_rel = rel_match[1]
            if formats_match:
                found_formats = formats_match[1]
            signposting_link_dict = {
                "url": found_link[1:-1],
                "type": str(found_type).strip(),
                "rel": str(found_rel).strip(),
                "profile": found_formats,
                "source": MetadataOfferingMethods.SIGNPOSTING.name,
                "origin": origin,
            }
            if anchor_match:
                signposting_link_dict["anchor"] = anchor_match[1]
            if signposting_link_dict.get("url") and signposting_link_dict.get("rel") in self.signposting_relation_types:
                found_signposting_links.append(signposting_link_dict)
        return found_signposting_links

    def set_signposting_linkset_links(self):
        linksetlink = {}
        linksetlinks = self.get_links(["linkset", "api-catalog"])
        if linksetlinks:
            linksetlink = linksetlinks[0]  # we only need one linkset link
        try:
            if linksetlink.get("url"):
                requestHelper = RequestHelper(linksetlink.get("url"), self.logger)
                requestHelper.setAcceptType(AcceptTypes.linkset)
                _neg_source, linkset_data = requestHelper.content_negotiate(self.ch.get_metric("metadata_properties"))
                if isinstance(linkset_data, dict):
                    if isinstance(linkset_data.get("linkset"), list):
                        validlinkset = None
                        for candidatelinkset in linkset_data.get("linkset"):
                            if isinstance(candidatelinkset, dict):
                                # usual describedby etc links must refer via anchor to the landing page or pid
                                # but api-catalog may refer to another URL which represents an API link
                                if (
                                    candidatelinkset.get("anchor") in [self.url]
                                    or linksetlink.get("rel") == "api-catalog"
                                ):
                                    validlinkset = candidatelinkset
                                    break
                        if validlinkset:
                            for linktype, links in validlinkset.items():
                                if linktype != "anchor":
                                    if not isinstance(links, list):
                                        links = [links]
                                    for link in links:
                                        if linktype in self.signposting_relation_types:
                                            self.typed_links.append(
                                                {
                                                    "url": link.get("href"),
                                                    "type": link.get("type"),
                                                    "rel": linktype,
                                                    "profile": link.get("profile"),
                                                    "source": MetadataOfferingMethods.SIGNPOSTING.name,
                                                    "origin": "linkset",
                                                }
                                            )
                            self.logger.info(
                                self.ch.get_metric("metadata_properties")
                                + " : Found valid Signposting Linkset in provided JSON file"
                            )
                        else:
                            self.logger.warning(
                                self.ch.get_metric("metadata_properties")
                                + " : Found Signposting Linkset but none of the given anchors matches landing page or PID"
                            )
                    # print(self.typed_links)
                else:
                    validlinkset = False
                    if linkset_data:
                        parsed_links = self.parse_signposting_http_link_format(linkset_data.decode(), origin="linkset")
                        try:
                            if parsed_links[0].get("anchor"):
                                self.logger.info(
                                    self.ch.get_metric("metadata_properties")
                                    + " : Found valid Signposting Linkset in provided text file"
                                )
                                for parsed_link in parsed_links:
                                    if (
                                        parsed_link.get("anchor") in [self.url]
                                        or linksetlink.get("rel") == "api-catalog"
                                    ):
                                        self.typed_links.append(parsed_link)
                                        validlinkset = True
                                if not validlinkset:
                                    self.logger.warning(
                                        self.ch.get_metric("metadata_properties")
                                        + " : Found Signposting Linkset but none of the given anchors matches landing page or PID"
                                    )
                        except Exception as e:
                            self.logger.warning(
                                self.ch.get_metric("metadata_properties")
                                + " : Found Signposting Linkset but could not correctly parse the file"
                            )
                            print(e)
                    else:
                        self.logger.warning(
                            self.ch.get_metric("metadata_properties")
                            + " : Found Signposting Linkset but could not correctly parse the file"
                        )
        except Exception as e:
            self.logger.warning(
                self.ch.get_metric("metadata_properties") + " : Failed to parse Signposting Linkset -: " + str(e)
            )

    def get_links(self, rel="item", origin="header", allkeys=True):
        # Use Typed Links in HTTP Link headers to help machines find the resources that make up a publication.
        # Use links to find domains specific metadata
        datalinks = []
        if not isinstance(rel, list):
            rel = [rel]
        if not isinstance(origin, list):
            origin = [origin]
        if not origin:
            origin = ["header", "linkset", "content"]
        for typed_link in self.typed_links:
            if typed_link.get("rel") in rel and typed_link.get("origin") in origin:
                if not allkeys:
                    typed_link = {tlkey: typed_link[tlkey] for tlkey in ["url", "type", "source"]}
                datalinks.append(typed_link)
        return datalinks
