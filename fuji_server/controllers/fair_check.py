# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import hashlib
import io
import logging
import logging.handlers
import re
from urllib.parse import urlparse

import pandas as pd

from fuji_server import __version__
from fuji_server.evaluators.fair_evaluator_api import FAIREvaluatorAPI
from fuji_server.evaluators.fair_evaluator_code_provenance import FAIREvaluatorCodeProvenance
from fuji_server.evaluators.fair_evaluator_community_metadata import FAIREvaluatorCommunityMetadata
from fuji_server.evaluators.fair_evaluator_data_access_level import FAIREvaluatorDataAccessLevel
from fuji_server.evaluators.fair_evaluator_data_content_metadata import FAIREvaluatorDataContentMetadata
from fuji_server.evaluators.fair_evaluator_data_identifier_included import FAIREvaluatorDataIdentifierIncluded
from fuji_server.evaluators.fair_evaluator_data_provenance import FAIREvaluatorDataProvenance
from fuji_server.evaluators.fair_evaluator_development_metadata import FAIREvaluatorDevelopmentMetadata
from fuji_server.evaluators.fair_evaluator_file_format import FAIREvaluatorFileFormat
from fuji_server.evaluators.fair_evaluator_formal_metadata import FAIREvaluatorFormalMetadata
from fuji_server.evaluators.fair_evaluator_license import FAIREvaluatorLicense
from fuji_server.evaluators.fair_evaluator_license_file import FAIREvaluatorLicenseFile
from fuji_server.evaluators.fair_evaluator_metadata_identifier_included import FAIREvaluatorMetadataIdentifierIncluded
from fuji_server.evaluators.fair_evaluator_metadata_preservation import FAIREvaluatorMetadataPreserved
from fuji_server.evaluators.fair_evaluator_minimal_metadata import FAIREvaluatorCoreMetadata
from fuji_server.evaluators.fair_evaluator_persistent_identifier_data import FAIREvaluatorPersistentIdentifierData
from fuji_server.evaluators.fair_evaluator_persistent_identifier_metadata import (
    FAIREvaluatorPersistentIdentifierMetadata,
)
from fuji_server.evaluators.fair_evaluator_related_resources import FAIREvaluatorRelatedResources
from fuji_server.evaluators.fair_evaluator_requirements import FAIREvaluatorRequirements
from fuji_server.evaluators.fair_evaluator_searchable import FAIREvaluatorSearchable
from fuji_server.evaluators.fair_evaluator_semantic_vocabulary import FAIREvaluatorSemanticVocabulary
from fuji_server.evaluators.fair_evaluator_software_component_identifier import FAIREvaluatorSoftwareComponentIdentifier
from fuji_server.evaluators.fair_evaluator_standardised_protocol_data import FAIREvaluatorStandardisedProtocolData
from fuji_server.evaluators.fair_evaluator_standardised_protocol_metadata import (
    FAIREvaluatorStandardisedProtocolMetadata,
)
from fuji_server.evaluators.fair_evaluator_test_cases import FAIREvaluatorTestCases
from fuji_server.evaluators.fair_evaluator_unique_identifier_data import FAIREvaluatorUniqueIdentifierData
from fuji_server.evaluators.fair_evaluator_unique_identifier_metadata import FAIREvaluatorUniqueIdentifierMetadata
from fuji_server.evaluators.fair_evaluator_unique_persistent_identifier_software import (
    FAIREvaluatorUniquePersistentIdentifierSoftware,
)
from fuji_server.evaluators.fair_evaluator_version_identifier import FAIREvaluatorVersionIdentifier
from fuji_server.harvester.data_harvester import DataHarvester
from fuji_server.harvester.github_harvester import GithubHarvester
from fuji_server.harvester.metadata_harvester import MetadataHarvester
from fuji_server.helper.linked_vocab_helper import linked_vocab_helper
from fuji_server.helper.metadata_collector import MetadataOfferingMethods
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.metric_helper import MetricHelper
from fuji_server.helper.preprocessor import Preprocessor
from fuji_server.helper.repository_helper import RepositoryHelper


class FAIRCheck:
    METRICS = None
    METRIC_VERSION = None
    SPDX_LICENSES = None
    SPDX_LICENSE_NAMES = None
    """COMMUNITY_METADATA_STANDARDS_NAMES = None
    COMMUNITY_METADATA_STANDARDS_URIS = None
    COMMUNITY_METADATA_STANDARDS = None"""
    SCIENCE_FILE_FORMATS = None
    LONG_TERM_FILE_FORMATS = None
    OPEN_FILE_FORMATS = None
    DEFAULT_NAMESPACES = None
    VOCAB_NAMESPACES = None
    ARCHIVE_MIMETYPES = Mapper.ARCHIVE_COMPRESS_MIMETYPES.value
    STANDARD_PROTOCOLS = None
    SCHEMA_ORG_CONTEXT = []
    FILES_LIMIT = None
    LOG_SUCCESS = 25
    LOG_FAILURE = 35
    VALID_RESOURCE_TYPES = []
    IDENTIFIERS_ORG_DATA = {}
    GOOGLE_DATA_DOI_CACHE = []
    GOOGLE_DATA_URL_CACHE = []
    LINKED_VOCAB_INDEX = {}
    ACCESS_RIGHTS = {}
    FUJI_VERSION = __version__

    def __init__(
        self,
        uid,
        test_debug=False,
        metadata_service_url=None,
        metadata_service_type=None,
        use_datacite=True,
        use_github=False,
        verify_pids=True,
        oaipmh_endpoint=None,
        metric_version=None,
    ):  # e.g. metrics_v0.5 regex: metrics_v([0-9]+\.[0-9]+)(_[a-z]+)?
        uid_bytes = uid.encode("utf-8")
        self.test_id = hashlib.sha1(uid_bytes).hexdigest()
        # str(base64.urlsafe_b64encode(uid_bytes), "utf-8") # an id we can use for caching etc
        if isinstance(uid, str):
            uid = uid.strip()
        self.id = self.input_id = uid

        self.metadata_service_url = metadata_service_url
        self.metadata_service_type = metadata_service_type
        self.oaipmh_endpoint = oaipmh_endpoint
        self.csw_endpoint = None
        self.sparql_endpoint = None
        if self.oaipmh_endpoint:
            self.metadata_service_url = self.oaipmh_endpoint
            self.metadata_service_type = "oai_pmh"
        if self.metadata_service_type == "oai_pmh":
            self.oaipmh_endpoint = self.metadata_service_url
        elif str(self.metadata_service_type) == "ogc_csw" or "csw" in str(self.metadata_service_type):
            self.csw_endpoint = self.metadata_service_url
        elif self.metadata_service_type == "sparql":
            self.sparql_endpoint = self.metadata_service_url
        self.pid_url = None  # full pid # e.g., "https://doi.org/10.1594/pangaea.906092 or url (non-pid)
        self.landing_url = None  # url of the landing page of self.pid_url
        self.origin_url = None  # the url from where all starts - in case of redirection we'll need this later on
        self.repository_urls = []  # urls identified which could represent the repository
        self.landing_html = None
        self.landing_content_type = None
        self.landing_origin = None  # schema + authority of the landing page e.g. https://www.pangaea.de
        self.signposting_header_links = []
        self.typed_links = []
        self.pid_scheme = None
        self.id_scheme = None
        self.checked_pages = []
        self.logger = logging.getLogger(self.test_id)
        self.metadata_sources = []
        self.isDebug = test_debug
        self.isLandingPageAccessible = None
        self.metadata_merged = {}
        self.metadata_unmerged = []
        self.content_identifier = {}
        self.community_standards = []
        self.community_standards_uri = {}
        self.namespace_uri = []
        self.linked_namespace_uri = {}
        self.reference_elements = (
            Mapper.REFERENCE_METADATA_LIST.value.copy()
        )  # all metadata elements required for FUJI metrics
        self.related_resources = []
        # self.test_data_content_text = None# a helper to check metadata against content
        self.rdf_graph = None

        self.rdf_collector = None
        self.use_datacite = use_datacite
        self.use_github = use_github
        self.repeat_pid_check = False
        self.logger_message_stream = io.StringIO()
        logging.addLevelName(self.LOG_SUCCESS, "SUCCESS")
        logging.addLevelName(self.LOG_FAILURE, "FAILURE")

        # in case log messages shall be sent to a remote server
        self.remoteLogPath = None
        self.remoteLogHost = None
        self.weblogger = None
        if self.isDebug:
            self.logStreamHandler = logging.StreamHandler(self.logger_message_stream)
            formatter = logging.Formatter("%(message)s|%(levelname)s")
            self.logStreamHandler.setFormatter(formatter)
            self.logger.propagate = False
            self.logger.setLevel(logging.INFO)  # set to debug in testing environment
            self.logger.addHandler(self.logStreamHandler)

            if Preprocessor.remote_log_host:
                self.weblogger = logging.handlers.HTTPHandler(
                    Preprocessor.remote_log_host,
                    Preprocessor.remote_log_path + "?testid=" + str(self.test_id),
                    method="POST",
                )
                self.webformatter = logging.Formatter("%(levelname)s - %(message)s \r\n")
        self.verify_pids = verify_pids
        if not self.verify_pids:
            self.logger.warning(
                "FsF-F1-02 : Verification of PIDs is disabled in the config file, the evaluation result may be misleading"
            )
        self.count = 0
        FAIRCheck.load_predata()
        # self.extruct = None
        self.extruct_result = {}
        self.lov_helper = linked_vocab_helper(self.LINKED_VOCAB_INDEX)
        self.auth_token = None
        self.auth_token_type = "Basic"

        self.pid_collector = {}
        if not metric_version:
            metric_version = "metrics_v0.5"
            self.logger.warning("FsF-F1-02 : Metrics version not given, therefore loading default metrics v0.5")
        self.metric_helper = MetricHelper(metric_version)
        self.METRICS = self.metric_helper.get_custom_metrics(
            ["metric_name", "total_score", "metric_tests", "metric_number"]
        )
        self.METRIC_VERSION = metric_version
        self.metrics_config = self.metric_helper.get_metrics_config()
        print("METRICS CONFIG: ", self.metrics_config)
        allowed_harvesting_methods = self.metrics_config.get("allowed_harvesting_methods")
        allowed_metadata_standards = self.metrics_config.get("allowed_metadata_standards")
        if not isinstance(allowed_metadata_standards, list):
            allowed_metadata_standards = None
        else:
            print("ALLOWED METADATA STANDARDS: ", allowed_metadata_standards)
        if allowed_harvesting_methods:
            print("ALLOWED METADATA OFFERING METHODS: ", allowed_harvesting_methods)
            if not isinstance(allowed_harvesting_methods, list):
                allowed_harvesting_methods = None
            else:
                allowed_harvesting_methods = [
                    MetadataOfferingMethods[m]
                    for m in allowed_harvesting_methods
                    if m in MetadataOfferingMethods._member_names_
                ]
        self.metadata_harvester = MetadataHarvester(
            self.id,
            use_datacite=use_datacite,
            logger=self.logger,
            allowed_harvesting_methods=allowed_harvesting_methods,
            allowed_metadata_standards=allowed_metadata_standards,
        )
        self.repo_helper = None

    @classmethod
    def load_predata(cls):
        cls.FILES_LIMIT = Preprocessor.data_files_limit
        if not cls.SPDX_LICENSES:
            cls.SPDX_LICENSES, cls.SPDX_LICENSE_NAMES = Preprocessor.get_licenses()
        """if not cls.COMMUNITY_METADATA_STANDARDS:
            cls.COMMUNITY_METADATA_STANDARDS = Preprocessor.get_metadata_standards()
            cls.COMMUNITY_METADATA_STANDARDS_URIS = {u.strip().strip('#/') : k for k, v in cls.COMMUNITY_METADATA_STANDARDS.items() for u in v.get('urls')}
            cls.COMMUNITY_METADATA_STANDARDS_NAMES = {k: v.get('title') for k,v in cls.COMMUNITY_METADATA_STANDARDS.items()}"""
        if not cls.SCIENCE_FILE_FORMATS:
            cls.SCIENCE_FILE_FORMATS = Preprocessor.get_science_file_formats()
        if not cls.LONG_TERM_FILE_FORMATS:
            cls.LONG_TERM_FILE_FORMATS = Preprocessor.get_long_term_file_formats()
        if not cls.OPEN_FILE_FORMATS:
            cls.OPEN_FILE_FORMATS = Preprocessor.get_open_file_formats()
        if not cls.DEFAULT_NAMESPACES:
            cls.DEFAULT_NAMESPACES = Preprocessor.getDefaultNamespaces()
        if not cls.VOCAB_NAMESPACES:
            cls.VOCAB_NAMESPACES = Preprocessor.getLinkedVocabs()
        if not cls.STANDARD_PROTOCOLS:
            cls.STANDARD_PROTOCOLS = Preprocessor.get_standard_protocols()
        if not cls.SCHEMA_ORG_CONTEXT:
            cls.SCHEMA_ORG_CONTEXT = Preprocessor.get_schema_org_context()
        if not cls.VALID_RESOURCE_TYPES:
            cls.VALID_RESOURCE_TYPES = Preprocessor.get_resource_types()
        if not cls.IDENTIFIERS_ORG_DATA:
            cls.IDENTIFIERS_ORG_DATA = Preprocessor.get_identifiers_org_data()
        if not cls.LINKED_VOCAB_INDEX:
            cls.LINKED_VOCAB_INDEX = Preprocessor.get_linked_vocab_index()
        if not cls.ACCESS_RIGHTS:
            cls.ACCESS_RIGHTS = Preprocessor.get_access_rights()
        # TODO: change this
        # Preprocessor.set_mime_types()

        # not needed locally ... but init class variable
        # Preprocessor.get_google_data_dois()
        # Preprocessor.get_google_data_urls()

    @staticmethod
    def uri_validator(u):  # TODO integrate into request_helper.py
        try:
            r = urlparse(u)
            return all([r.scheme, r.netloc])
        except:
            return False

    def set_auth_token(self, auth_token, auth_token_type="Basic"):
        if auth_token:
            self.auth_token = auth_token
            self.metadata_harvester.auth_token = self.auth_token
        if auth_token_type:
            if auth_token_type in ["Basic", "Bearer"]:
                self.auth_token_type = auth_token_type
                self.metadata_harvester.auth_token_type = self.auth_token_type
            else:
                self.auth_token_type = "Basic"

    def clean_metadata(self):
        data_objects = self.metadata_merged.get("object_content_identifier")
        if data_objects == {"url": None} or data_objects == [None]:
            data_objects = self.metadata_merged["object_content_identifier"] = None
        if data_objects is not None:
            if not isinstance(data_objects, list):
                self.metadata_merged["object_content_identifier"] = [data_objects]

        # TODO quick-fix to merge size information - should do it at mapper
        if "object_content_identifier" in self.metadata_merged:
            if self.metadata_merged.get("object_content_identifier"):
                oi = 0
                for c in self.metadata_merged["object_content_identifier"]:
                    if not c.get("size") and self.metadata_merged.get("object_size"):
                        c["size"] = self.metadata_merged.get("object_size")
                    # clean mime types in case these are in URI form:
                    if c.get("type"):
                        if isinstance(c["type"], list):
                            c["type"] = c["type"][0]
                            self.metadata_merged["object_content_identifier"][oi]["type"] = c["type"][0]
                        mime_parts = str(c.get("type")).split("/")
                        if len(mime_parts) > 2:
                            if mime_parts[-2] in [
                                "application",
                                "audio",
                                "font",
                                "example",
                                "image",
                                "message",
                                "model",
                                "multipart",
                                "text",
                                "video",
                            ]:
                                self.metadata_merged["object_content_identifier"][oi]["type"] = (
                                    str(mime_parts[-2]) + "/" + str(mime_parts[-1])
                                )
                    oi += 1
        # clean empty entries
        for mk, mv in list(self.metadata_merged.items()):
            if mv == "" or mv is None:
                del self.metadata_merged[mk]

    def harvest_all_metadata(self):
        # ========= clean merged metadata, delete all entries which are None or ''
        self.retrieve_metadata_embedded()
        self.retrieve_metadata_external()
        self.clean_metadata()
        self.logger.info(
            "FsF-F2-01M : Type of object described by the metadata -: {}".format(
                self.metadata_merged.get("object_type")
            )
        )
        # detect api and standards
        # self.retrieve_apis_standards()
        # remove duplicates
        if self.namespace_uri:
            self.namespace_uri = list(set(self.namespace_uri))

    def harvest_re3_data(self):
        if self.use_datacite:
            client_id = self.metadata_merged.get("datacite_client")
            self.logger.info(f"FsF-R1.3-01M : re3data/datacite client id -: {client_id}")
            self.repo_helper = RepositoryHelper(client_id=client_id, logger=self.logger, landingpage=self.landing_url)
            self.repo_helper.lookup_re3data()
        else:
            self.client_id = None
            self.logger.warning(
                "{} : Datacite support disabled, therefore skipping standards identification using in re3data record".format(
                    "FsF-R1.3-01M",
                )
            )

    def harvest_all_data(self):
        if self.metadata_merged.get("object_content_identifier"):
            data_links = self.metadata_merged.get("object_content_identifier")  # [: self.FILES_LIMIT]
            data_harvester = DataHarvester(data_links, self.logger, self.landing_url, metrics=self.METRICS.keys())
            data_harvester.retrieve_all_data()
            self.content_identifier = data_harvester.data

    def harvest_github(self):
        if self.use_github:
            github_harvester = GithubHarvester(self.id)
            github_harvester.harvest()
            self.github_data = github_harvester.data
        else:
            self.github_data = {}
            # NOTE: Update list of metrics that are impacted by this as more are implemented.
            for m in ["FRSM-15-R1.1"]:
                self.logger.warning(f"{m} : Github support disabled, therefore skipping harvesting through Github API")

    def retrieve_metadata_embedded(self):
        self.metadata_harvester.retrieve_metadata_embedded()
        self.metadata_unmerged.extend(self.metadata_harvester.metadata_unmerged)
        self.metadata_merged.update(self.metadata_harvester.metadata_merged)
        self.repeat_pid_check = self.metadata_harvester.repeat_pid_check
        self.namespace_uri.extend(self.metadata_harvester.namespace_uri)
        self.metadata_sources.extend(self.metadata_harvester.metadata_sources)
        self.linked_namespace_uri.update(self.metadata_harvester.linked_namespace_uri)
        self.related_resources.extend(self.metadata_harvester.related_resources)
        self.landing_url = self.metadata_harvester.landing_url
        self.landing_origin = self.metadata_harvester.landing_origin
        self.landing_domain = self.metadata_harvester.landing_domain
        self.origin_url = self.metadata_harvester.origin_url
        self.pid_url = self.metadata_harvester.pid_url
        self.pid_scheme = self.metadata_harvester.pid_scheme
        self.pid_collector.update(self.metadata_harvester.pid_collector)

    def retrieve_metadata_external(self, target_url=None, repeat_mode=False):
        self.metadata_harvester.retrieve_metadata_external(target_url, repeat_mode=repeat_mode)
        self.metadata_unmerged.extend(self.metadata_harvester.metadata_unmerged)
        self.metadata_merged.update(self.metadata_harvester.metadata_merged)
        self.repeat_pid_check = self.metadata_harvester.repeat_pid_check
        self.namespace_uri.extend(self.metadata_harvester.namespace_uri)
        self.metadata_sources.extend(self.metadata_harvester.metadata_sources)
        self.linked_namespace_uri.update(self.metadata_harvester.linked_namespace_uri)
        self.related_resources.extend(self.metadata_harvester.related_resources)
        self.metadata_harvester.get_signposting_object_identifier()
        self.pid_collector.update(self.metadata_harvester.pid_collector)

    """def lookup_metadatastandard_by_name(self, value):
        found = None
        # get standard name with the highest matching percentage using fuzzywuzzy
        highest = process.extractOne(value, FAIRCheck.COMMUNITY_METADATA_STANDARDS_NAMES, scorer=fuzz.token_sort_ratio)
        if highest[1] > 80:
            found = highest[2]
        return found

    def lookup_metadatastandard_by_uri(self, value):
        found = None
        if value:
            value = str(value).strip().strip('#/')
            # try to find it as direct match using http or https as prefix
            if value.startswith('http') or value.startswith('ftp'):
                value = value.replace('s://', '://')
                found = FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS.get(value)
                if not found:
                    found = FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS.get(value.replace('://', 's://'))
            if not found:
                #fuzzy as fall back
                try:
                    match = process.extractOne(value,
                                               FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS.keys())
                    if extract(str(value)).domain == extract(str(match[1]).domain):
                        if match[1] > 90:
                            found = list(FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS.values())[match[2]]
                except Exception as e:
                    pass
        return found"""

    def check_unique_metadata_identifier(self):
        unique_identifier_check = FAIREvaluatorUniqueIdentifierMetadata(self)
        return unique_identifier_check.getResult()

    def check_unique_content_identifier(self):
        unique_identifier_check = FAIREvaluatorUniqueIdentifierData(self)
        return unique_identifier_check.getResult()

    def check_persistent_metadata_identifier(self):
        persistent_identifier_check = FAIREvaluatorPersistentIdentifierMetadata(self)
        return persistent_identifier_check.getResult()

    def check_persistent_data_identifier(self):
        persistent_identifier_check = FAIREvaluatorPersistentIdentifierData(self)
        return persistent_identifier_check.getResult()

    def check_unique_persistent_metadata_identifier(self):
        # self.metadata_harvester.get_signposting_object_identifier()
        return self.check_unique_metadata_identifier(), self.check_persistent_metadata_identifier()

    def check_unique_persistent_software_identifier(self):
        unique_persistent_identifier_check = FAIREvaluatorUniquePersistentIdentifierSoftware(self)
        return unique_persistent_identifier_check.getResult()

    def check_software_component_identifier(self):
        component_identifier_check = FAIREvaluatorSoftwareComponentIdentifier(self)
        return component_identifier_check.getResult()

    def check_version_identifier(self):
        version_identifier_check = FAIREvaluatorVersionIdentifier(self)
        return version_identifier_check.getResult()

    def check_development_metadata(self):
        development_metadata_check = FAIREvaluatorDevelopmentMetadata(self)
        return development_metadata_check.getResult()

    def check_open_api(self):
        open_api_check = FAIREvaluatorAPI(self)
        return open_api_check.getResult()

    def check_requirements(self):
        requirements_check = FAIREvaluatorRequirements(self)
        return requirements_check.getResult()

    def check_test_cases(self):
        test_cases_check = FAIREvaluatorTestCases(self)
        return test_cases_check.getResult()

    def check_minimal_metatadata(self, include_embedded=True):
        core_metadata_check = FAIREvaluatorCoreMetadata(self)
        return core_metadata_check.getResult()

    def check_data_identifier_included_in_metadata(self):
        data_identifier_included_check = FAIREvaluatorDataIdentifierIncluded(self)
        return data_identifier_included_check.getResult()

    def check_metadata_identifier_included_in_metadata(self):
        metadata_identifier_included_check = FAIREvaluatorMetadataIdentifierIncluded(self)
        return metadata_identifier_included_check.getResult()

    def check_data_access_level(self):
        data_access_level_check = FAIREvaluatorDataAccessLevel(self)
        return data_access_level_check.getResult()

    def check_license(self):
        license_check = FAIREvaluatorLicense(self)
        return license_check.getResult()

    def check_license_file(self):
        license_check = FAIREvaluatorLicenseFile(self)
        return license_check.getResult()

    def check_relatedresources(self):
        related_check = FAIREvaluatorRelatedResources(self)
        return related_check.getResult()

    def check_searchable(self):
        searchable_check = FAIREvaluatorSearchable(self)
        return searchable_check.getResult()

    def check_data_file_format(self):
        data_file_check = FAIREvaluatorFileFormat(self)
        return data_file_check.getResult()

    def check_community_metadatastandards(self):
        community_metadata_check = FAIREvaluatorCommunityMetadata(self)
        return community_metadata_check.getResult()

    def check_data_provenance(self):
        data_prov_check = FAIREvaluatorDataProvenance(self)
        return data_prov_check.getResult()

    def check_code_provenance(self):
        code_prov_check = FAIREvaluatorCodeProvenance(self)
        return code_prov_check.getResult()

    def check_data_content_metadata(self):
        data_content_metadata_check = FAIREvaluatorDataContentMetadata(self)
        return data_content_metadata_check.getResult()

    def check_formal_metadata(self):
        formal_metadata_check = FAIREvaluatorFormalMetadata(self)
        return formal_metadata_check.getResult()

    def check_semantic_vocabulary(self):
        semantic_vocabulary_check = FAIREvaluatorSemanticVocabulary(self)
        return semantic_vocabulary_check.getResult()

    def check_metadata_preservation(self):
        metadata_preserved_check = FAIREvaluatorMetadataPreserved(self)
        return metadata_preserved_check.getResult()

    def check_standardised_protocol_data(self):
        standardised_protocol_check = FAIREvaluatorStandardisedProtocolData(self)
        return standardised_protocol_check.getResult()

    def check_standardised_protocol_metadata(self):
        standardised_protocol_metadata_check = FAIREvaluatorStandardisedProtocolMetadata(self)
        return standardised_protocol_metadata_check.getResult()

    """def raise_warning_if_javascript_page(self, response_content):
        # check if javascript generated content only:
        try:
            soup = BeautifulSoup(response_content, features="html.parser")
            script_content = soup.findAll("script")
            for script in soup(["script", "style", "title", "noscript"]):
                script.extract()

            text_content = soup.get_text(strip=True)
            if (len(str(script_content)) > len(str(text_content))) and len(text_content) <= 150:
                self.logger.warning(
                    "FsF-F1-02D : Landing page seems to be JavaScript generated, could not detect enough content"
                )
        except Exception:
            pass
"""

    def get_log_messages_dict(self):
        logger_messages = {}
        self.logger_message_stream.seek(0)
        for log_message in self.logger_message_stream.readlines():
            if log_message.startswith("FsF-") or log_message.startswith("FRSM-"):
                m = log_message.split(":", 1)
                metric = m[0].strip()
                message_n_level = m[1].strip().split("|", 1)
                if len(message_n_level) > 1:
                    level = message_n_level[1]
                else:
                    level = "INFO"
                message = message_n_level[0]
                if metric not in logger_messages:
                    logger_messages[metric] = []
                if message not in logger_messages[metric]:
                    logger_messages[metric].append(level.replace("\n", "") + ": " + message.strip())
        self.logger_message_stream = io.StringIO

        return logger_messages

    def get_assessment_summary(self, results):
        status_dict = {"pass": 1, "fail": 0}
        summary_dict = {
            "fair_category": [],
            "fair_principle": [],
            "score_earned": [],
            "score_total": [],
            "maturity": [],
            "status": [],
        }
        for res_k, res_v in enumerate(results):
            if res_v.get("metric_identifier"):
                metric_match = re.search(
                    r"^(?:FRSM-[0-9]+|FsF)-(([FAIR])[0-9](\.[0-9])?)", str(res_v.get("metric_identifier"))
                )  # match both FAIR and FsF metrics
                if metric_match.group(2) is not None:
                    fair_principle = metric_match[1]
                    fair_category = metric_match[2]
                    earned_maturity = res_v["maturity"]
                    # earned_maturity = [k for k, v in maturity_dict.items() if v == res_v['maturity']][0]
                    summary_dict["fair_category"].append(fair_category)
                    summary_dict["fair_principle"].append(fair_principle)
                    # An easter egg for Mustapha
                    if self.input_id in [
                        "https://www.rd-alliance.org/users/mustapha-mokrane",
                        "https://www.rd-alliance.org/users/ilona-von-stein",
                    ]:
                        summary_dict["score_earned"].append(res_v["score"]["total"])
                        summary_dict["maturity"].append(3)
                        summary_dict["status"].append(1)
                    else:
                        summary_dict["score_earned"].append(res_v["score"]["earned"])
                        summary_dict["maturity"].append(earned_maturity)
                        summary_dict["status"].append(status_dict.get(res_v["test_status"]))
                    summary_dict["score_total"].append(res_v["score"]["total"])
        sf = pd.DataFrame(summary_dict)
        summary = {"score_earned": {}, "score_total": {}, "score_percent": {}, "status_total": {}, "status_passed": {}}

        summary["score_earned"] = sf.groupby(by="fair_category")["score_earned"].sum().to_dict()
        summary["score_earned"].update(sf.groupby(by="fair_principle")["score_earned"].sum().to_dict())
        summary["score_earned"]["FAIR"] = round(float(sf["score_earned"].sum()), 2)

        summary["score_total"] = sf.groupby(by="fair_category")["score_total"].sum().to_dict()
        summary["score_total"].update(sf.groupby(by="fair_principle")["score_total"].sum().to_dict())
        summary["score_total"]["FAIR"] = round(float(sf["score_total"].sum()), 2)

        summary["score_percent"] = (
            round(
                sf.groupby(by="fair_category")["score_earned"].sum()
                / sf.groupby(by="fair_category")["score_total"].sum()
                * 100,
                2,
            )
        ).to_dict()
        summary["score_percent"].update(
            (
                round(
                    sf.groupby(by="fair_principle")["score_earned"].sum()
                    / sf.groupby(by="fair_principle")["score_total"].sum()
                    * 100,
                    2,
                )
            ).to_dict()
        )
        summary["score_percent"]["FAIR"] = round(float(sf["score_earned"].sum() / sf["score_total"].sum() * 100), 2)

        summary["maturity"] = (
            sf.groupby(by="fair_category")["maturity"]
            .apply(lambda x: 1 if x.mean() < 1 and x.mean() > 0 else round(x.mean()))
            .to_dict()
        )
        summary["maturity"].update(
            sf.groupby(by="fair_principle")["maturity"]
            .apply(lambda x: 1 if x.mean() < 1 and x.mean() > 0 else round(x.mean()))
            .to_dict()
        )
        total_maturity = 0
        for fair_index in ["F", "A", "I", "R"]:
            if summary["maturity"].get(fair_index):
                total_maturity += summary["maturity"][fair_index]
        summary["maturity"]["FAIR"] = round(
            float(1 if total_maturity / 4 < 1 and total_maturity / 4 > 0 else total_maturity / 4), 2
        )

        summary["status_total"] = sf.groupby(by="fair_principle")["status"].count().to_dict()
        summary["status_total"].update(sf.groupby(by="fair_category")["status"].count().to_dict())
        summary["status_total"]["FAIR"] = int(sf["status"].count())

        summary["status_passed"] = sf.groupby(by="fair_principle")["status"].sum().to_dict()
        summary["status_passed"].update(sf.groupby(by="fair_category")["status"].sum().to_dict())
        summary["status_passed"]["FAIR"] = int(sf["status"].sum())
        return summary

    def set_repository_uris(self):
        if self.landing_origin:
            self.repository_urls.append(self.landing_origin)
            if self.metadata_merged.get("publisher"):
                if not isinstance(self.metadata_merged.get("publisher"), list):
                    self.metadata_merged["publisher"] = [self.metadata_merged.get("publisher")]
                for publisher_url in self.metadata_merged.get("publisher"):
                    if self.uri_validator(publisher_url):
                        if self.landing_domain in publisher_url:
                            self.repository_urls.append(publisher_url)
        if self.repository_urls:
            self.repository_urls = list(set(self.repository_urls))
        print("REPOSITORY: ", self.repository_urls)
