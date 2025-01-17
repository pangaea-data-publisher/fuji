# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import re
import urllib
import uuid

import hashid
import idutils

from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.request_helper import AcceptTypes, RequestHelper


class IdentifierHelper:
    # List of PIDS e.g. those listed in datacite schema
    VALID_PIDS = {
        "ark": {"label": "Archival Resource Key (ARK)", "source": "datacite.org"},
        "arxiv": {"label": "arXiv Submission ID", "source": "datacite.org"},
        "bioproject": {"label": "BioProject ID", "source": "identifiers.org"},
        "biosample": {"label": "BioSample ID", "source": "identifiers.org"},
        "doi": {"label": "Digital Object Identifier (DOI)", "source": "datacite.org"},
        "ensembl": {"label": "Ensembl ID", "source": "identifiers.org"},
        "genome": {"label": "GenBank or RefSeq genome", "source": "identifiers.org"},
        "gnd": {"label": "Gemeinsame Normdatei (GND) ID", "source": "f-uji.net"},
        "handle": {"label": "Handle System ID", "source": "datacite.org"},
        "lsid": {"label": "Life Science Identifier", "source": "datacite.org"},
        "pmid": {"label": "PubMed ID", "source": "datacite.org"},
        "pmcid": {"label": "PubMed Central ID", "source": "identifiers.org"},
        "purl": {"label": "Persistent Uniform Resource Locator (PURL)", "source": "datacite.org"},
        "refseq": {"label": "RefSeq ID", "source": "identifiers.org"},
        "sra": {"label": "Sequence Read Archive (SRA) ID", "source": "identifiers.org"},
        "uniprot": {"label": "UniProt ID", "source": "identifiers.org"},
        "urn": {"label": "Uniform Resource Name (URN)", "source": "datacite.org"},
        "identifiers.org": {"label": "Identifiers.org Identifier", "source": "identifiers.org"},
        "w3id": {"label": "Permanent Identifier for the Web (W3ID)", "source": "identifiers.org"},
    }
    # identifiers.org pattern
    # TODO: check if this is needed.. if so ..complete and add check to FAIRcheck
    IDENTIFIERS_PIDS = r"https://identifiers.org/[provider_code/]namespace:accession"

    IDENTIFIERS_ORG_DATA = Preprocessor.get_identifiers_org_data()
    identifier_schemes = []
    preferred_schema = None  # the preferred schema
    identifier_url = None
    identifier = None
    method = "idutils"
    resolver = None
    is_persistent = False
    NON_IDENTIFIERS_ORG_KEYS = ["doi"]
    URN_RESOLVER = {
        "urn:doi:": "dx.doi.org/",
        "urn:lex:br": "www.lexml.gov.br/",
        "urn:nbn:de": "nbn-resolving.org/",
        "urn:nbn:se": "urn.kb.se/resolve?urn=",
        "urn:nbn:at": "resolver.obvsg.at/",
        "urn:nbn:hr": "urn.nsk.hr/",
        "urn:nbn:no": "urn.nb.no/",
        "urn:nbn:fi": "urn.fi/",
        "urn:nbn:it": "nbn.depositolegale.it/",
        "urn:nbn:nl": "www.persistent-identifier.nl/",
    }

    # check if the urn is a urn plus resolver URL
    def check_resolver_urn(self, idstring):
        ret = False
        if "urn:" in idstring and not idstring.startswith("urn:"):
            try:
                urnsplit = re.split(r"(urn:(?:nbn|doi|lex|):[a-z]+)", idstring, re.IGNORECASE)
                if len(urnsplit) > 1:
                    urnid = urnsplit[1]
                    candidateurn = urnid + str(urnsplit[2])
                    candresolver = re.sub(r"https?://", "", urnsplit[0])
                    if candresolver in self.URN_RESOLVER.values():
                        if idutils.is_urn(candidateurn):
                            self.identifier_schemes = ["url", "urn"]
                            self.preferred_schema = "urn"
                            self.normalized_id = candidateurn
                            self.identifier_url = "https://" + candresolver + candidateurn
                            ret = True
            except Exception as e:
                print("URN parsing error", e)
        return ret

    def __init__(self, idstring, logger=None):
        self.identifier = idstring
        self.normalized_id = None
        self.logger = logger
        if self.identifier and isinstance(self.identifier, str):
            idparts = urllib.parse.urlparse(self.identifier)
            if len(self.identifier) > 4 and not self.identifier.isnumeric():
                # workaround to identify nbn urns given together with standard resolver urls:
                self.check_resolver_urn(self.identifier)
                # workaround to resolve lsids:
                # idutils.LANDING_URLS['lsid'] ='http://www.lsid.info/resolver/?lsid={pid}'
                # workaround to recognize https purls and arks
                if "/purl.archive.org/" in self.identifier:
                    self.identifier = self.identifier.replace("/purl.archive.org/", "/purl.org/")
                if "https://purl." in self.identifier or "/ark:" in self.identifier:
                    self.identifier = self.identifier.replace("https:", "http:")
                # workaround to identify arks properly:
                self.identifier = self.identifier.replace("/ark:", "/ark:/")
                self.identifier = self.identifier.replace("/ark://", "/ark:/")
                generic_identifiers_org_pattern = r"^([a-z0-9\._]+):(.+)"

                if self.is_uuid():
                    self.identifier_schemes = ["uuid"]
                    self.preferred_schema = "uuid"
                    self.is_persistent = False
                if self.is_hash():
                    self.identifier_schemes = ["hash"]
                    self.preferred_schema = "hash"
                    self.is_persistent = False

                if not self.identifier_schemes or self.identifier_schemes == ["url"]:
                    # w3id check
                    if (
                        idparts.scheme == "https"
                        and idparts.netloc in ["w3id.org", "www.w3id.org"]
                        and idparts.path != ""
                    ):
                        self.identifier_schemes = ["w3id", "url"]
                        self.preferred_schema = "w3id"
                        self.identifier_url = self.identifier
                        self.normalized_id = self.identifier
                    # identifiers.org

                    elif idparts.netloc == "identifiers.org":
                        idorgparts = idparts.path.split("/")
                        if len(idorgparts) == 3:
                            self.identifier = idorgparts[1] + ":" + idorgparts[2]

                    idmatch = re.search(generic_identifiers_org_pattern, self.identifier)
                    if idmatch:
                        found_prefix = idmatch[1]
                        found_suffix = idmatch[2]
                        if (
                            found_prefix in self.IDENTIFIERS_ORG_DATA.keys()
                            and found_prefix not in self.NON_IDENTIFIERS_ORG_KEYS
                        ):
                            if re.search(self.IDENTIFIERS_ORG_DATA[found_prefix]["pattern"], found_suffix):
                                self.identifier_schemes = ["identifiers.org", found_prefix]
                                self.preferred_schema = found_prefix
                                self.identifier_url = "https://identifiers.org/" + str(self.identifier)

                                """self.identifier_url = str(
                                    self.IDENTIFIERS_ORG_DATA[found_prefix]["url_pattern"]
                                ).replace("{$id}", found_suffix)"""
                                self.normalized_id = found_prefix.lower() + ":" + found_suffix

                # idutils check
                if not self.identifier_schemes:
                    self.identifier_schemes = idutils.detect_identifier_schemes(self.identifier)
                    if "url" not in self.identifier_schemes and idparts.scheme in ["http", "https"]:
                        self.identifier_schemes.append("url")
                # verify handles
                if "handle" in self.identifier_schemes:
                    if not self.verify_handle(self.identifier):
                        self.identifier_schemes.remove("handle")
                # identifiers.org check
                if self.identifier_schemes:
                    # preferred schema
                    if self.identifier_schemes:
                        if len(self.identifier_schemes) > 0:
                            if len(self.identifier_schemes) > 1:
                                if "url" in self.identifier_schemes:  # ['doi', 'url']
                                    # move url to end of list
                                    self.identifier_schemes.append(
                                        self.identifier_schemes.pop(self.identifier_schemes.index("url"))
                                    )
                                    # self.identifier_schemes.remove('url')
                            self.preferred_schema = self.identifier_schemes[0]
                            if not self.normalized_id:
                                self.normalized_id = idutils.normalize_pid(self.identifier, self.preferred_schema)
                            if not self.identifier_url:
                                self.identifier_url = self.to_url(self.identifier, self.preferred_schema)
                            # print('IDURL ',self.identifier_url, self.preferred_schema)
                if (
                    self.preferred_schema in self.VALID_PIDS
                    or self.preferred_schema in self.IDENTIFIERS_ORG_DATA.keys()
                ):
                    self.is_persistent = True
            if not self.normalized_id:
                self.normalized_id = self.identifier

    def is_uuid(self):
        try:
            uuid_version = uuid.UUID(self.identifier).version
            if uuid_version is not None:
                return True
            else:
                return False
        except ValueError:
            return False

    def is_hash(self):
        try:
            hash = hashid.HashID()
            validhash = False
            for hashtype in hash.identifyHash(self.identifier):
                if re.search(r"^(sha|md5|blake)", hashtype.name, re.IGNORECASE):
                    validhash = True
            return validhash
        except Exception:
            return False

    def verify_handle(self, val, includeparams=True):
        # additional checks for handles since the syntax is very generic
        try:
            # see: https://www.icann.org/en/system/files/files/octo-002-14oct19-en.pdf :
            # One of the Handle System's main features is that prefixes do not include names. Dr. Kahn
            # explains that the Handle System "does not rely on name semantics". For example, organization
            # names are usually not included in handle prefixes. To date, except for a few special (and
            # primarily administrative) cases, prefixes contain only digits.
            # Therefore:
            # handle_regexp = re.compile(r"(hdl:\s*|(?:https?://)?hdl\.handle\.net/)?([^/.]+(?:\.[^/.]+)*)/(.+)$")
            handle_regexp = re.compile(
                r"(hdl:\s*|(?:https?://)?hdl\.handle\.net/)?([0-9]+(?:\.[0-9]+)*)/(.+)$", flags=re.I
            )
            ures = urllib.parse.urlparse(val)
            if ures:
                if ures.query:
                    # detect handles in uri
                    for query in ures.query.split("&"):
                        try:
                            param = query.split("=")[1]
                            if param.startswith("hdl.handle") or param.startswith("hdl:"):
                                val = param
                        except Exception:
                            pass
            m = handle_regexp.match(val)
            if m:
                return True
            else:
                return False
        except Exception as e:
            print("handle verification error: " + str(e))
            return False

    def to_url(self, id, schema):
        idurl = None
        try:
            if schema == "ark":
                idurl = id
            else:
                idurl = idutils.to_url(id, schema)
            if schema in ["doi", "handle"]:
                idurl = idurl.replace("http:", "https:")
        except Exception as e:
            print("ID helper to_url error " + str(e))
        return idurl

    def get_resolved_url(self, pid_collector={}):
        candidate_pid = self.identifier_url
        if candidate_pid not in pid_collector or not pid_collector:
            try:
                requestHelper = RequestHelper(candidate_pid, self.logger)
                requestHelper.setAcceptType(AcceptTypes.default)  # request
                requestHelper.content_negotiate("FsF-F1-02D", ignore_html=False)
                if requestHelper.response_content:
                    return requestHelper.redirect_url, requestHelper.status_list
                else:
                    return None, requestHelper.status_list
            except Exception as e:
                print("PID resolve test error", e)
                return None
        else:
            return pid_collector[candidate_pid].get("landing_page")

    def get_preferred_schema(self):
        return self.preferred_schema

    def get_identifier_schemes(self):
        return self.identifier_schemes

    def get_identifier_url(self):
        return self.identifier_url

    def get_normalized_id(self):
        return self.normalized_id

    def get_identifier_info(self, pidcollector={}, resolve=True):
        if resolve:
            resolved_url, status_list = self.get_resolved_url(pidcollector)
        else:
            resolved_url, status_list = None, None
        return {
            "pid": self.identifier,
            "normalized": self.normalized_id,
            "pid_url": self.identifier_url,
            "scheme": self.preferred_schema,
            "is_persistent": self.is_persistent,
            "resolved_url": resolved_url,
            "status_list": status_list,
        }
