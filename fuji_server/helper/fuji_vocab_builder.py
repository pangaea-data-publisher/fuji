# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import json
import os

import yaml
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.helper.linked_vocab_helper import LinkedVocabHelper
from fuji_server.helper.metadata_collector import (
    MetadataFormats,
    MetadataOfferingMethods,
    metadata_mapper,
)


class fuji_knowledge_base:
    def __init__(self, root=""):
        self.namespace = "https://f-uji.net/vocab"
        self.vocabdict = {
            self.namespace + "/metadata": {
                "uri": self.namespace + "/metadata",
                "label": "Metadata",
                "description": "Everything about metadata",
                "source": "f-uji.net",
            },
            self.namespace + "/data": {
                "uri": self.namespace + "/data",
                "label": "Data",
                "description": "Everything about data, usually the item(s) which is/are described by metadata",
                "source": "f-uji.net",
            },
            self.namespace + "/identifier": {
                "uri": self.namespace + "/identifier",
                "label": "Digital Identifier",
                "description": "A name or identifier which identifies a digital object",
                "source": "f-uji.net",
            },
            self.namespace + "/access_condition": {
                "uri": self.namespace + "/access_condition",
                "label": "Access Conditions",
                "description": "Information concerning the accessibility of resources, especially about existing restrictions.",
                "source": "f-uji.net",
            },
        }
        self.root = root
        base_path = os.path.abspath(os.path.dirname(__file__))
        self.fuji_data_path = os.path.join(base_path, "..", "data")

    def get_vocab_dict(self):
        self.add_transport_protocol()
        self.add_identifiers()
        self.add_metadata_properties()
        self.add_metadata_methods()
        self.add_metadata_formats()
        self.add_metadata_exchange_method()
        self.add_metadata_standards()
        self.add_semantic_resources()
        self.add_licenses()
        self.add_file_types()
        self.add_data_properties()
        self.add_access_rights()
        return self.vocabdict
        # self.add_metadata_methods('metadata/method')

    def add_transport_protocol(self):
        parentkey = "transport_protocol"
        prdict = {}
        with open(os.path.join(self.fuji_data_path, "standard_uri_protocols.yaml"), encoding="utf-8") as acf:
            protocol_dict = yaml.safe_load(acf)
        for protocolid, protocol in protocol_dict.items():
            prdict[self.namespace + "/" + parentkey + "/" + protocolid] = {
                "label": protocol.get("name"),
                "uri": self.namespace + "/" + parentkey + "/" + protocolid,
                "broader": self.namespace + "/" + parentkey,
            }

        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/transport_protocol",
            "label": "Transport Protocol",
            "description": "Transport protocols used to handle data or metadata ideally via the internet.",
            "source": "f-uji.net",
        }
        self.vocabdict.update(prdict)
        return prdict

    def add_access_rights(self):
        parentkey = "access_condition"
        ac_dict = {}
        with open(os.path.join(self.fuji_data_path, "access_rights.yaml"), encoding="utf-8") as acf:
            access_rights_dict = yaml.safe_load(acf)
        for access_source in access_rights_dict.values():
            ac_dict[self.namespace + "/" + parentkey + "/" + access_source.get("id")] = {
                "label": access_source.get("label"),
                "uri": self.namespace + "/" + parentkey + "/" + access_source.get("id"),
                "identifier": access_source.get("identifier"),
                "broader": self.namespace + "/" + parentkey,
                "source": access_source.get("source"),
            }
            for access_info in access_source.get("members"):
                ac_dict[
                    self.namespace + "/" + parentkey + "/" + access_source.get("id") + "/" + access_info.get("id")
                ] = {
                    "label": access_info.get("label"),
                    "uri": self.namespace
                    + "/"
                    + parentkey
                    + "/"
                    + access_source.get("id")
                    + "/"
                    + access_info.get("id"),
                    "identifier": {"value": access_info.get("uri"), "type": "homepage"},
                    "broader": self.namespace + "/" + parentkey + "/" + access_source.get("id"),
                    "source": access_info.get("source"),
                }
        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Access Conditions",
            "description": "Information concerning the accessibility of resources, especially about existing restrictions.",
            "source": "f-uji.net",
        }
        self.vocabdict.update(ac_dict)
        return ac_dict

    # serialisation: html, json, json-ld, rdf (ttl, n3), xml
    def add_identifiers(self):
        id_dict = {}
        parentkey = "identifier/unique"
        identifiers = {
            "url": {"label": "Uniform Resource Locator", "source": "datacite.org"},
            "iri": {"label": "Internationalized Resource Identifier", "source": ""},
            "uuid": {"label": "Universally Unique Identifier", "source": ""},
            "hash": {"label": "Hash Code", "source": ""},
        }
        for idk, idv in identifiers.items():
            id_dict[self.namespace + "/" + parentkey + "/" + idk] = {
                "label": idv.get("label"),
                "uri": self.namespace + "/" + parentkey + "/" + idk,
                "broader": self.namespace + "/" + parentkey,
                "source": idv.get("source"),
            }
        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Unique Identifier",
            "broader": self.namespace + "/identifier",
            "source": "f-uji.net",
        }
        self.vocabdict.update(id_dict)

        parentkey = "identifier/persistent"
        identifiers = IdentifierHelper.VALID_PIDS
        for idk, idv in identifiers.items():
            id_dict[self.namespace + "/" + parentkey + "/" + idk] = {
                "label": idv.get("label"),
                "uri": self.namespace + "/" + parentkey + "/" + idk,
                "broader": self.namespace + "/" + parentkey,
                "source": idv.get("source"),
            }

        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Persistent Identifier",
            "broader": self.namespace + "/identifier",
            "source": "f-uji.net",
        }
        self.vocabdict.update(id_dict)

    def add_data_properties(self):
        parentkey = "data/property/"
        self.vocabdict[self.namespace + "/" + parentkey + "/size"] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Data (File) Size",
            "broader": self.namespace + "/" + parentkey,
            "source": "f-uji.net",
        }
        self.vocabdict[self.namespace + "/" + parentkey + "/url"] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Data (File) Identifier (URI)",
            "broader": self.namespace + "/" + parentkey,
            "source": "f-uji.net",
        }
        self.vocabdict[self.namespace + "/" + parentkey + "/type"] = {
            "uri": self.namespace + "/" + "/data",
            "alias": "url",
            "label": "Data Type (Mime Type)",
            "broader": self.namespace + "/data",
            "narrower": self.namespace + "/data/format",
            "source": "f-uji.net",
        }
        self.vocabdict[self.namespace + "/" + parentkey + "/service"] = {
            "uri": self.namespace + "/" + "/data",
            "alias": "service",
            "label": "Data Service",
            "broader": self.namespace + "/data",
            "source": "f-uji.net",
        }

    def add_metadata_properties(self):
        parentkey = "metadata/property"
        properties_dict = {}
        properties = metadata_mapper.Mapper.REFERENCE_METADATA_LIST.value
        if properties:
            for propkey, propvalue in properties.items():
                propvalue["source"] = "f-uji.net"
                propvalue["uri"] = str(self.namespace) + "/" + parentkey + "/" + str(propkey)
                propvalue["broader"] = self.namespace + "/" + parentkey
                properties_dict[self.namespace + "/" + parentkey + "/" + propkey] = propvalue
            self.vocabdict[self.namespace + "/" + parentkey] = {
                "uri": self.namespace + "/" + parentkey,
                "label": "Metadata Property",
                "description": "",
                "broader": self.namespace + "/metadata",
                "source": "f-uji.net",
            }
            self.vocabdict.update(properties_dict)

    def add_relation_types(self):
        reltype_dict = {}
        parentkey = "relation_type"
        for rel in metadata_mapper.Mapper.DC_MAPPING.value.get("related_resources"):
            reltype_dict[self.namespace + "/" + parentkey + "/" + rel] = {
                "label": rel,
                "broader": self.namespace + "/" + parentkey,
                "uri": self.namespace + "/" + parentkey + "/" + rel,
                "sameAs": "http://purl.org/dc/terms/" + rel,
                "source": "dublincore.org",
            }
        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Relation Types",
            "description": "Terms describing the type of relation between digital entities. This list is based on but not restricted to those defined by dublin core. Internally, relation types other than DC terms are mappred to dc terms",
            "broader": self.namespace,
            "source": "f-uji.net",
        }
        self.vocabdict.update(reltype_dict)

    def add_metadata_formats(self):
        parentkey = "metadata/format"
        metamethod_dict = {}
        for method in MetadataFormats:
            metamethod_dict[self.namespace + "/" + parentkey + "/" + method.acronym()] = {
                "label": method.value.get("label"),
                "broader": self.namespace + "/" + parentkey,
                "uri": self.namespace + "/" + parentkey + "/" + method.acronym(),
                "source": "f-uji.net",
            }
        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Metadata Format",
            "description": "Formats in which metadata van be serialised such as XML, RDF etc.",
            "broader": self.namespace + "/metadata",
            "source": "f-uji.net",
        }
        self.vocabdict.update(metamethod_dict)

    def add_metadata_methods(self):
        parentkey = "metadata/offering_method"
        metamethod_dict = {}
        for method in MetadataOfferingMethods:
            metamethod_dict[self.namespace + "/" + parentkey + "/" + method.acronym()] = {
                "label": method.value.get("label"),
                "broader": self.namespace + "/" + parentkey,
                "uri": self.namespace + "/" + parentkey + "/" + method.acronym(),
                "source": "f-uji.net",
            }
        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Metadata Offering Method",
            "description": "",
            "broader": self.namespace + "/metadata",
            "source": "f-uji.net",
        }
        self.vocabdict.update(metamethod_dict)

    def add_metadata_standards(self):
        parentkey = "metadata/standard"
        metastandards_dict = {}
        with open(os.path.join(self.fuji_data_path, "metadata_standards.yaml")) as mdf:
            mddict = yaml.safe_load(mdf)
            for mk, mv in mddict.items():
                mk = mk.replace(".yml", "")
                sources = []
                identifiers = []
                for ident in mv.get("identifier"):
                    if ident.get("type") in ["namespace", "schema", "homepage"]:
                        identifiers.append(ident)
                    if ident.get("value"):
                        if "msc:" in ident.get("value"):
                            sources.append("rd-alliance.org")
                        elif "fairsharing.org" in ident.get("value"):
                            sources.append("fairsharing.org")
                        elif "www.dcc.ac" in ident.get("value"):
                            sources.append("dcc.ac")
                metastandards_dict[self.namespace + "/" + parentkey + "/" + mk] = {
                    "label": mv.get("title"),
                    "uri": self.namespace + "/" + parentkey + "/" + mk,
                    "broader": self.namespace + "/" + parentkey,
                    "identifier": identifiers,
                    "field_of_science": mv.get("field_of_science"),
                    "source": sources,
                }
                self.vocabdict[self.namespace + "/" + parentkey] = {
                    "uri": self.namespace + "/" + parentkey,
                    "label": "Metadata Standard",
                    "description": "",
                    "broader": self.namespace + "/metadata",
                    "source": "f-uji.net",
                }
                self.vocabdict.update(metastandards_dict)

    def add_semantic_resources(self):
        parentkey = "semantic_resource"
        semanticdict = {}
        lov_helper = LinkedVocabHelper()
        lov_helper.set_linked_vocab_dict()
        linked_vocab_index = lov_helper.linked_vocab_dict
        for lovk, lovv in linked_vocab_index.items():
            identifiers = []
            if lovv.get("uri_format"):
                namespace = str(lovv.get("uri_format")).replace("$1", "")
                identifiers.append({"type": "namespace", "value": namespace})
            if lovv.get("homepage"):
                homepage = str(lovv.get("homepage"))
                identifiers.append({"type": "homepage", "value": homepage})
            semanticdict[self.namespace + "/" + parentkey + "/" + lovk] = {
                "uri": self.namespace + "/" + parentkey + "/" + lovk,
                "broader": self.namespace + "/" + parentkey,
                "label": lovv.get("name"),
                "identifier": identifiers,
                "source": lovv.get("source"),
                "field_of_science": lovv.get("subjects"),
            }
            self.vocabdict[self.namespace + "/" + parentkey] = {
                "uri": self.namespace + "/" + parentkey,
                "label": "Semantic Resource",
                "description": "",
                "source": "f-uji.net",
            }
            self.vocabdict.update(semanticdict)

    def add_licenses(self):
        parentkey = "license"
        license_dict = {}
        with open(os.path.join(self.fuji_data_path, "licenses.yaml")) as lcd:
            license_list = yaml.safe_load(lcd)
            for lic in license_list:
                license_dict[self.namespace + "/" + parentkey + "/" + lic.get("licenseId")] = {
                    "uri": self.namespace + "/" + parentkey + "/" + lic.get("licenseId"),
                    "broader": self.namespace + "/" + parentkey,
                    "label": lic.get("name"),
                    "identifier": [
                        {
                            "type": "homepage",
                            "value": str(lic.get("reference")).replace("./", "https://spdx.org/licenses/"),
                        },
                        {"type": "schema", "value": lic.get("detailsUrl")},
                    ],
                    "source": "spdx.org",
                }
        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/" + parentkey,
            "label": "Licenses",
            "description": "",
            "source": "f-uji.net",
        }
        self.vocabdict.update(license_dict)

    def add_metadata_exchange_method(self):
        service_dict = {
            self.namespace + "/metadata/exchange_service": {
                "uri": self.namespace + "/metadata/exchange_service",
                "label": "Metadata Exchange Service",
                "description": "Standardised services which are used to exchange metadata between machines",
                "source": "f-uji.net",
            },
            self.namespace + "/metadata/exchange_service/oai_pmh": {
                "uri": self.namespace + "/metadata/exchange_service/oai_pmh",
                "label": "OAI-PMH",
                "broader": self.namespace + "/metadata/exchange_service",
                "description": "Open Archives Initiative Protocol for Metadata Harvesting",
                "source": "f-uji.net",
            },
            self.namespace + "/metadata/exchange_service/ogc_csw": {
                "uri": self.namespace + "/metadata/exchange_service/ogc_csw",
                "label": "OGC CSW",
                "broader": self.namespace + "/metadata/exchange_service",
                "description": "Catalogue Service for the Web",
                "source": "f-uji.net",
            },
            self.namespace + "/metadata/exchange_service/sparql": {
                "uri": self.namespace + "/metadata/exchange_service/sparql",
                "label": "SPARQL",
                "broader": self.namespace + "/metadata/exchange_service",
                "description": "SPARQL Protocol and RDF Query Language",
                "source": "f-uji.net",
            },
        }
        self.vocabdict.update(service_dict)

    def add_file_types(self):
        parentkey = "data/format"
        filedict = {}
        with open(os.path.join(self.fuji_data_path, "file_formats.yaml")) as lcd:
            file_format_list = yaml.safe_load(lcd)
            for ffk, ffv in file_format_list.items():
                identifiers = []
                for mime in ffv.get("mime"):
                    identifiers.append({"type": "mime", "value": mime})
                filedict[self.namespace + "/" + parentkey + "/" + ffk] = {
                    "uri": self.namespace + "/" + parentkey + "/" + ffk,
                    "label": ffv.get("name"),
                    "broader": self.namespace + "/" + parentkey,
                    "identifier": identifiers,
                    "source": ffv.get("source"),
                    "type": ffv.get("reason"),
                }
        self.vocabdict[self.namespace + "/" + parentkey] = {
            "uri": self.namespace + "/" + parentkey,
            "broader": self.namespace + "/data",
            "label": "Data Format",
            "description": "",
            "source": "f-uji.net",
        }
        self.vocabdict.update(filedict)


fb = fuji_knowledge_base()
vocabdir = "C:\\xampp\\htdocs\\fuji\\.vocab"
for tk, tv in fb.get_vocab_dict().items():
    print(tk.replace(fb.namespace, ""))
    # if tv.get('broader'):
    termid = tk.split("/")[-1]
    termdir = vocabdir + "/".join(tk.split("/")[:-1]).replace(fb.namespace, "").replace("/", "\\")
    print(termdir)
    # termdir = vocabdir+tv.get('broader').replace(fb.namespace,'').replace('/','\\')
    os.makedirs(termdir, exist_ok=True)
    with open(termdir + "\\" + termid + ".json", "w") as termfile:
        json.dump(tv, termfile)
# add_metadata_properties('metadata/property')
# fb.add_relation_types()
# print(fuji_vocab_dict)

# print(add_licenses('metadata/licenses'))
# print(add_semantic_resources('metadata/licenses'))
