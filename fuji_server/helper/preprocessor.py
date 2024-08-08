# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import json
import logging
import mimetypes
import os
import time
from urllib.parse import urlparse

import requests

import yaml
from fuji_server.helper.linked_vocab_helper import linked_vocab_helper


class Preprocessor:
    # static elements belong to the class.
    _instance = None

    all_metrics_list = []
    formatted_specification = {}
    bool_string = {"true": True, "false": False}
    total_metrics = 0
    total_licenses = 0
    METRIC_YML_PATH = None
    SPDX_URL = "https://raw.github.com/spdx/license-list-data/master/json/licenses.json"
    DATACITE_API_REPO = "https://api.datacite.org/repositories"
    RE3DATA_API = "https://re3data.org/api/beta/repositories"
    LOV_API = None
    LOD_CLOUDNET = None
    BIOPORTAL_API = None
    BIOPORTAL_KEY = None

    schema_org_context = []
    schema_org_creativeworks = []
    all_licenses = []
    license_names = []
    metadata_standards = {}  # key=subject,value =[standards name]
    metadata_standards_uris = {}  # some additional namespace uris and all uris from above as key
    all_file_formats = {}
    science_file_formats = {}
    long_term_file_formats = {}
    open_file_formats = {}
    access_rights = {}
    re3repositories: dict[str, str] = {}
    linked_vocabs = {}
    linked_vocab_index = {}
    default_namespaces = []
    standard_protocols = {}
    resource_types = []
    identifiers_org_data = {}
    google_data_dois = []
    google_data_urls = []
    # fuji_server_dir = os.path.dirname(sys.modules['__main__'].__file__)
    fuji_server_dir = os.path.dirname(os.path.dirname(__file__))  # project_root
    header = {"Accept": "application/json"}
    logger = logging.getLogger(__name__)
    data_files_limit = 3
    metric_specification = None
    remote_log_host = None
    remote_log_path = None
    verify_pids = False
    max_content_size = 5000000
    google_custom_search_id = None
    google_custom_search_api_key = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def set_mime_types(cls):
        try:
            mimes = requests.get("https://raw.githubusercontent.com/jshttp/mime-db/master/db.json").json()
            for mime_type, mime_data in mimes.items():
                if mime_data.get("extensions"):
                    for ext in mime_data.get("extensions"):
                        # if '.' + ext not in mimetypes.types_map:
                        mimetypes.add_type(mime_type, "." + ext, strict=True)
            print(len(mimetypes.types_map))
        except Exception:
            cls.logger.warning("Loading additional mime types failed, will continue with standard set")

    @classmethod
    def set_max_content_size(cls, size):
        cls.max_content_size = int(size)

    @classmethod
    def set_remote_log_info(cls, host, path):
        if host:
            try:
                request = requests.get("http://" + host + path)
                if request.status_code == 200:
                    cls.remote_log_host = host
                    cls.remote_log_path = path
                else:
                    cls.logger.warning("Remote Logging not possible, URL response: " + str(request.status_code))
            except Exception:
                cls.logger.warning("Remote Logging not possible ,please correct : " + str(host) + " " + str(path))

    @classmethod
    def set_verify_pids(cls, verify):
        # if str(verify).lower in self.bool_string:
        cls.verify_pids = cls.bool_string.get(str(verify).lower)
        # cls.verify_pids = verify

    @classmethod
    def set_google_custom_search_info(cls, search_id, api_key, web_search):
        if api_key:
            cls.google_custom_search_id = search_id
            cls.google_custom_search_api_key = api_key
            cls.google_web_search_enabled = web_search

    @classmethod
    def get_identifiers_org_data(cls):
        if not cls.identifiers_org_data:
            cls.retrieve_identifiers_org_data()
        return cls.identifiers_org_data

    @classmethod
    def retrieve_identifiers_org_data(cls):
        std_uri_path = os.path.join(cls.fuji_server_dir, "data", "identifiers_org_resolver_data.json")
        with open(std_uri_path, encoding="utf8") as f:
            identifiers_data = json.load(f)
        if identifiers_data:
            for namespace in identifiers_data["payload"]["namespaces"]:
                cls.identifiers_org_data[namespace["prefix"]] = {
                    "pattern": namespace["pattern"],
                    "url_pattern": namespace["resources"][0]["urlPattern"],
                }

    @classmethod
    def get_resource_types(cls):
        if not cls.resource_types:
            cls.retrieve_resource_types()
        return cls.resource_types

    @classmethod
    def retrieve_resource_types(cls):
        ns = []
        ns_file_path = os.path.join(cls.fuji_server_dir, "data", "ResourceTypes.txt")
        with open(ns_file_path) as f:
            ns = [line.lower().rstrip() for line in f]
        if ns:
            cls.resource_types = ns

    @classmethod
    def retrieve_schema_org_context(cls):
        data = {}
        std_uri_path = os.path.join(cls.fuji_server_dir, "data", "jsonldcontext.json")
        with open(std_uri_path) as f:
            data = json.load(f)
        if data:
            for context, schemadict in data.get("@context").items():
                if isinstance(schemadict, dict):
                    schemauri = schemadict.get("@id")
                    if str(schemauri).startswith("schema:"):
                        cls.schema_org_context.append(str(context).lower())
            bioschema_context = cls.get_schema_org_creativeworks()
            cls.schema_org_context.extend(bioschema_context)
            cls.schema_org_context = list(set(cls.schema_org_context))

    @classmethod
    def retrieve_schema_org_creativeworks(cls, include_bioschemas=True):
        data = []
        cw_path = os.path.join(cls.fuji_server_dir, "data", "creativeworktypes.txt")
        with open(cw_path) as f:
            data = f.read().splitlines()
        if include_bioschemas:
            bs_path = os.path.join(cls.fuji_server_dir, "data", "bioschemastypes.txt")
            with open(bs_path) as f:
                bdata = f.read().splitlines()
                data.extend(bdata)
        cls.schema_org_creativeworks = [item.lower() for item in data]

    @classmethod
    def get_schema_org_creativeworks(cls, include_bioschemas=True):
        if not cls.schema_org_creativeworks:
            cls.retrieve_schema_org_creativeworks(include_bioschemas)
        return cls.schema_org_creativeworks

    @classmethod
    def get_schema_org_context(cls):
        if not cls.schema_org_context:
            cls.retrieve_schema_org_context()
        return cls.schema_org_context

    @classmethod
    def set_data_files_limit(cls, limit):
        cls.data_files_limit = limit

    @classmethod
    def set_metric_yaml_path(cls, yaml_metric_path):
        cls.METRIC_YML_PATH = yaml_metric_path

    @classmethod
    def retrieve_metrics_yaml(cls, yaml_metric_path):
        cls.METRIC_YML_PATH = yaml_metric_path
        # cls.data_files_limit = limit
        # cls.metric_specification = specification_uri
        stream = open(cls.METRIC_YML_PATH, encoding="utf8")
        try:
            specification = yaml.load(stream, Loader=yaml.FullLoader)
        except yaml.YAMLError as e:
            cls.logger.error(e)
        cls.all_metrics_list = specification["metrics"]
        cls.total_metrics = len(cls.all_metrics_list)

        # expected output format of http://localhost:1071/uji/api/v1/metrics
        # unwanted_keys = ['question_type']
        cls.formatted_specification["total"] = cls.total_metrics
        # temp_list = []
        # for dictm in cls.all_metrics_list:
        # temp_dict = {k: v for k, v in dictm.items() if k not in unwanted_keys}
        # temp_list.append(dictm)
        # cls.formatted_specification['metrics'] = temp_list
        cls.formatted_specification["metrics"] = cls.all_metrics_list

    @classmethod
    def retrieve_datacite_re3repos(cls):
        # retrieve all client id and re3data doi from datacite
        isDebugMode = True
        re3dict_path = os.path.join(cls.fuji_server_dir, "data", "repodois.yaml")
        repolistdate = os.path.getmtime(re3dict_path)
        try:
            # update once a day
            if time.time() - repolistdate >= 86400:
                isDebugMode = False
        except:
            pass
        if isDebugMode:
            with open(re3dict_path) as f:
                cls.re3repositories = yaml.safe_load(f)
        else:
            print("updating re3data dois")
            p = {"query": "re3data_id:*"}
            try:
                req = requests.get(cls.DATACITE_API_REPO, params=p, headers=cls.header, timeout=5)
                raw = req.json()
                for r in raw["data"]:
                    cls.re3repositories[r["id"]] = r["attributes"]["re3data"]
                while "next" in raw["links"]:
                    response = requests.get(raw["links"]["next"]).json()
                    for r in response["data"]:
                        cls.re3repositories[r["id"]] = r["attributes"]["re3data"]
                    raw["links"] = response["links"]
                # fix wrong entry
                cls.re3repositories["bl.imperial"] = "http://doi.org/10.17616/R3K64N"
                with open(re3dict_path, "w") as f2:
                    yaml.dump(cls.re3repositories, f2)

            except requests.exceptions.RequestException as e:
                os.utime(re3dict_path)
                print("Preprocessor Error: " + str(e))
                cls.logger.error(e)

    @classmethod
    def get_access_rights(cls):
        data = None
        jsn_path = os.path.join(cls.fuji_server_dir, "data", "access_rights.json")
        with open(jsn_path) as f:
            data = json.load(f)
        return data

    @classmethod
    def retrieve_licenses(cls, isDebugMode):
        data = None
        jsn_path = os.path.join(cls.fuji_server_dir, "data", "licenses.json")
        # The repository can be found at https://github.com/spdx/license-list-data
        # https://spdx.org/spdx-license-list/license-list-overview
        if isDebugMode:  # use local file instead of downloading the file online
            with open(jsn_path) as f:
                data = json.load(f)
        else:
            # cls.SPDX_URL = license_path
            try:
                r = requests.get(cls.SPDX_URL)
                try:
                    if r.status_code == 200:
                        resp = r.json()
                        data = resp["licenses"]
                        for d in data:
                            d["name"] = d["name"].lower()  # convert license name to lowercase
                        with open(jsn_path, "w") as f:
                            json.dump(data, f)
                except json.decoder.JSONDecodeError as e1:
                    cls.logger.error(e1)
            except requests.exceptions.RequestException as e2:
                cls.logger.error(e2)
        if data:
            cls.all_licenses = data
            for licenceitem in cls.all_licenses:
                seeAlso = licenceitem.get("seeAlso")
                # some cleanup to add modified licence URLs
                for licenceurl in seeAlso:
                    if "http:" in licenceurl:
                        altURL = licenceurl.replace("http:", "https:")
                    else:
                        altURL = licenceurl.replace("https:", "http:")
                    if altURL not in seeAlso:
                        seeAlso.append(altURL)
                    if licenceurl.endswith("/legalcode"):
                        altURL = licenceurl.replace("/legalcode", "")
                        seeAlso.append(altURL)
            cls.total_licenses = len(data)
            cls.license_names = [d["name"] for d in data if "name" in d]
            # referenceNumber = [r['referenceNumber'] for r in data if 'referenceNumber' in r]
            # seeAlso = [s['seeAlso'] for s in data if 'seeAlso' in s]
            # cls.license_urls = dict(zip(referenceNumber, seeAlso))

    @classmethod
    def retrieve_metadata_standards(cls):
        # cls.retrieve_metadata_standards_uris()
        data = {}
        std_path = os.path.join(cls.fuji_server_dir, "data", "metadata_standards.json")
        # The original repository can be retrieved via https://rdamsc.bath.ac.uk/api/m
        # or at https://github.com/rd-alliance/metadata-catalog-dev
        with open(std_path) as f:
            data = json.load(f)
        """else:
            try:
                r = requests.get(catalog_url)
                try:
                    if r.status_code == 200:
                        resp = r.json()
                        schemes = resp['metadata-schemes']
                        for s in schemes:
                            r2 = requests.get(catalog_url + str(s['id']), headers=cls.header)
                            if r2.status_code == 200:
                                std = r2.json()
                                urls = None
                                keywords = std.get('keywords')
                                standard_title = std.get('title')
                                locations = std.get('locations')
                                if locations:
                                    urls = [d['url'] for d in std.get('locations') if 'url' in d]
                                # if keywords:
                                # for k in keywords:
                                # data.setdefault(k.lower(), []).append(standard_title)
                                # else:
                                # data.setdefault('other', []).append(standard_title)
                                if standard_title:
                                    data[standard_title] = {'subject_areas': keywords, 'urls': urls}

                        with open(std_path, 'w') as f:
                            json.dump(data, f)
                except json.decoder.JSONDecodeError as e1:
                    cls.logger.error(e1)
            except requests.exceptions.RequestException as e2:
                cls.logger.error(e2)"""
        if data:
            cls.metadata_standards = data

    @classmethod
    def retrieve_all_file_formats(cls):
        data = {}
        sci_file_path = os.path.join(cls.fuji_server_dir, "data", "file_formats.json")
        with open(sci_file_path) as f:
            data = json.load(f)
        if data:
            cls.all_file_formats = data

    @classmethod
    def retrieve_science_file_formats(cls, isDebugMode):
        data = {}
        if not cls.all_file_formats:
            cls.retrieve_all_file_formats()
        for file in cls.all_file_formats.values():
            if "scientific format" in file.get("reason"):
                domain = None
                if file.get("domain"):
                    domain = file.get("domain")[0]
                for mime in file.get("mime"):
                    data[mime] = domain
        """sci_file_path = os.path.join(cls.fuji_server_dir, 'data', 'science_formats.json')
        with open(sci_file_path) as f:
            data = json.load(f)"""
        if data:
            cls.science_file_formats = data

    @classmethod
    def retrieve_long_term_file_formats(cls, isDebugMode):
        data = {}
        if not cls.all_file_formats:
            cls.retrieve_all_file_formats()
        for file in cls.all_file_formats.values():
            if "long term format" in file.get("reason"):
                domain = None
                if file.get("domain"):
                    domain = file.get("domain")[0]
                for mime in file.get("mime"):
                    data[mime] = domain
        """sci_file_path = os.path.join(cls.fuji_server_dir, 'data', 'longterm_formats.json')
        with open(sci_file_path) as f:
            data = json.load(f)"""
        if data:
            cls.long_term_file_formats = data

    @classmethod
    def retrieve_open_file_formats(cls, isDebugMode):
        data = {}
        if not cls.all_file_formats:
            cls.retrieve_all_file_formats()
        for file in cls.all_file_formats.values():
            if "open format" in file.get("reason"):
                domain = None
                if file.get("domain"):
                    domain = file.get("domain")[0]
                for mime in file.get("mime"):
                    data[mime] = domain
        """sci_file_path = os.path.join(cls.fuji_server_dir, 'data', 'open_formats.json')
        with open(sci_file_path) as f:
            data = json.load(f)"""
        if data:
            cls.open_file_formats = data

    @classmethod
    def retrieve_standard_protocols(cls, isDebugMode):
        data = {}
        protocols_path = os.path.join(cls.fuji_server_dir, "data", "standard_uri_protocols.json")
        with open(protocols_path) as f:
            data = json.load(f)
        if data:
            cls.standard_protocols = data

    @classmethod
    def retrieve_default_namespaces(cls):
        ns = []
        ns_file_path = os.path.join(cls.fuji_server_dir, "data", "default_namespaces.txt")
        with open(ns_file_path) as f:
            # ns = [line.split(':',1)[1].strip() for line in f]
            ns = [line.rstrip().rstrip("/#") for line in f]
        if ns:
            cls.default_namespaces = ns

    @classmethod
    def get_linked_vocab_index(cls):
        if not cls.linked_vocab_index:
            cls.retrieve_linked_vocab_index()
        return cls.linked_vocab_index

    @classmethod
    def retrieve_linked_vocab_index(cls):
        lov_helper = linked_vocab_helper()
        lov_helper.set_linked_vocab_index()
        cls.linked_vocab_index = lov_helper.linked_vocab_index

    @classmethod
    def retrieve_linkedvocabs(cls, lov_api, lodcloud_api, isDebugMode):
        # def retrieve_linkedvocabs(cls, lov_api, lodcloud_api, bioportal_api, bioportal_key, isDebugMode):
        # may take around 20 minutes to test and import all vocabs
        cls.LOV_API = lov_api
        cls.LOD_CLOUDNET = lodcloud_api
        # cls.BIOPORTAL_API = bioportal_api
        # cls.BIOPORTAL_KEY = bioportal_key
        ld_path = os.path.join(cls.fuji_server_dir, "data", "linked_vocab.json")
        vocabs = []
        if isDebugMode:
            with open(ld_path) as f:
                cls.linked_vocabs = json.load(f)
        else:
            # 1. retrieve records from https://lov.linkeddata.es/dataset/lov/api
            # 714 vocabs, of which 104 vocabs uri specified are broken (02072020)
            try:
                req = requests.get(lov_api, headers=cls.header)
                raw_lov = req.json()
                broken = []
                cls.logger.info(f"{len(raw_lov)} vocabs specified at {lov_api}")
                for lov in raw_lov:
                    title = next(i.get("value") for i in lov.get("titles") if i.get("lang") == "en")
                    uri = lov.get("uri")
                    nsp = lov.get("nsp")
                    if uri and nsp:
                        if cls.isURIActive(uri):
                            vocabs.append({"title": title, "namespace": nsp, "uri": uri, "prefix": lov.get("prefix")})
                        else:
                            broken.append(uri)
                    else:
                        broken.append(uri)
                cls.logger.info(f"{len(broken)} vocabs uri specified are broken")
            except requests.exceptions.RequestException as e:
                cls.logger.error(e)
            except requests.exceptions.ConnectionError as e1:
                cls.logger.error(e1)

            all_uris = [d["uri"] for d in vocabs if "uri" in d]
            # 2a. retrieve vocabs from https://lod-cloud.net/lod-data.json
            # 1440 vocabs specified of which 1008 broken, so this source may be excluded in future
            try:
                r = requests.get(lodcloud_api, headers=cls.header)
                raw = r.json()
                cls.logger.info(f"{len(raw)} vocabs specified at {lodcloud_api}")
                broken_lod = []
                for r in raw:
                    d = raw.get(r)
                    website = d.get("website")
                    ns = d.get("namespace")
                    if website and ns:
                        if cls.isURIActive(website):
                            if website not in all_uris:
                                temp = {
                                    "title": d["title"],
                                    "namespace": ns,
                                    "uri": website,
                                    "prefix": d.get("identifier"),
                                }
                                vocabs.append(temp)
                        else:
                            broken_lod.append(website)
                    else:
                        broken_lod.append(website)
                cls.logger.info(f"{len(broken_lod)} vocabs uri specified are broken")
            except requests.exceptions.RequestException as e:
                cls.logger.error(e)
            except requests.exceptions.ConnectionError as e1:
                cls.logger.error(e1)

            # 2b retrieve from BioPortal (excluded for now as the namespace in the ontology not necessarily use bioportal uri)
            # try:
            #     params = dict()
            #     params["apikey"] = bioportal_key
            #     r = requests.get(bioportal_api, params=params)
            #     onto_path = r.json()["links"]["ontologies"]
            #     resp = requests.get(onto_path, params=params)
            #     ontologies = resp.json()
            #     cls.logger.info('{0} vocabs specified at {1}'.format(len(ontologies), bioportal_api))
            #     broken_lod = []
            #     for onto in ontologies:
            #         title_onto = onto['name']
            #         prefix_onto = onto['acronym']
            #         uri_onto = onto['ui']
            # except requests.exceptions.RequestException as e:
            #     cls.logger.exception(e)
            # except requests.exceptions.ConnectionError as e1:
            #     cls.logger.exception(e1)

            # 3. write to a local file
            try:
                with open(ld_path, "w") as f:
                    json.dump(vocabs, f)
                    cls.linked_vocabs = vocabs
            except OSError:
                cls.logger.error(f"Couldn't write to file {ld_path}.")
        # for vocab in vocabs.items():

    @staticmethod
    def uri_validator(u):
        try:
            r = urlparse(u)
            return all([r.scheme, r.netloc])
        except:
            return False

    @classmethod
    def isURIActive(cls, url):
        isActive = False
        if cls.uri_validator(url):
            try:
                r = requests.head(url)
                if not (400 <= r.status_code < 600):
                    isActive = True
            except requests.exceptions.RequestException as e:
                cls.logger.error(e)
            except requests.exceptions.ConnectionError as e1:
                cls.logger.error(e1)
        return isActive

    @classmethod
    def get_licenses(cls):
        if not cls.all_licenses:
            cls.retrieve_licenses(True)
        return cls.all_licenses, cls.license_names

    @classmethod
    def getRE3repositories(cls):
        if not cls.re3repositories:
            cls.retrieve_datacite_re3repos()
        return cls.re3repositories

    @classmethod
    def getLinkedVocabs(cls):
        if not cls.linked_vocabs:
            # cls.retrieve_linkedvocabs(cls.LOV_API, cls.LOD_CLOUDNET, cls.BIOPORTAL_API, cls.BIOPORTAL_KEY, True)
            cls.retrieve_linkedvocabs(cls.LOV_API, cls.LOD_CLOUDNET, True)
        return cls.linked_vocabs

    @classmethod
    def getDefaultNamespaces(cls):
        if not cls.default_namespaces:
            cls.retrieve_default_namespaces()
        return cls.default_namespaces

    """@classmethod
    def get_metrics(cls):
        return cls.formatted_specification

    @classmethod
    def get_total_metrics(cls):
        return cls.total_metrics"""

    @classmethod
    def get_total_licenses(cls):
        return cls.total_licenses

    @classmethod
    def get_custom_metrics(cls, wanted_fields):
        new_dict = {}
        if not cls.all_metrics_list:
            cls.retrieve_metrics_yaml(cls.METRIC_YML_PATH)
        for dictm in cls.all_metrics_list:
            new_dict[dictm["metric_identifier"]] = {k: v for k, v in dictm.items() if k in wanted_fields}
        return new_dict

    @classmethod
    def get_metadata_standards(cls) -> object:
        if not cls.metadata_standards:
            cls.retrieve_metadata_standards()
        return cls.metadata_standards

    @classmethod
    def get_science_file_formats(cls) -> object:
        if not cls.science_file_formats:
            cls.retrieve_science_file_formats(True)
        return cls.science_file_formats

    @classmethod
    def get_long_term_file_formats(cls) -> object:
        if not cls.long_term_file_formats:
            cls.retrieve_long_term_file_formats(True)
        return cls.long_term_file_formats

    @classmethod
    def get_open_file_formats(cls) -> object:
        if not cls.open_file_formats:
            cls.retrieve_open_file_formats(True)
        return cls.open_file_formats

    @classmethod
    def get_standard_protocols(cls) -> object:
        if not cls.standard_protocols:
            cls.retrieve_standard_protocols(True)
        return cls.standard_protocols
