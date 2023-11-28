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


from tldextract import extract

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_provider_csw import OGCCSWMetadataProvider
from fuji_server.helper.metadata_provider_oai import OAIMetadataProvider
from fuji_server.helper.metadata_provider_sparql import SPARQLMetadataProvider
from fuji_server.models.community_endorsed_standard import CommunityEndorsedStandard
from fuji_server.models.community_endorsed_standard_output_inner import CommunityEndorsedStandardOutputInner


class FAIREvaluatorCommunityMetadata(FAIREvaluator):
    """
    A class to evaluate metadata that follows a standard recommended by the target research of the data (R.13-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate whether the metadata follows community specific metadata standard listed in, e.g., re3data,
        or metadata follows community specific metadata standard using namespaces or schemas found in the provided metadata
        or the metadata service outputs.
    """

    def __init__(self, fuji_instance):
        self.pids_which_resolve = {}
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-R1.3-01M")
        self.community_standards_output = []
        self.found_metadata_standards = []
        self.valid_metadata_standards = []

    def validate_service_url(self):
        # checks if service url and landing page url have same domain in order to avoid manipulations
        if self.fuji.metadata_service_url:
            service_url_parts = extract(self.fuji.metadata_service_url)
            landing_url_parts = extract(self.fuji.landing_url)
            service_domain = service_url_parts.domain + "." + service_url_parts.suffix
            landing_domain = landing_url_parts.domain + "." + landing_url_parts.suffix
            if landing_domain == service_domain:
                return True
            else:
                self.logger.warning(
                    "FsF-R1.3-01M : Service URL domain/subdomain does not match with landing page domain -: {}".format(
                        service_domain,
                    )
                )
                (
                    self.fuji.metadata_service_url,
                    self.fuji.csw_endpoint,
                    self.fuji.oaipmh_endpoint,
                    self.fuji.sparql_endpoint,
                ) = (None, None, None, None)
                return False
        else:
            return False

    def retrieve_metadata_standards_from_namespaces(self):
        nsstandards = []
        if self.fuji.namespace_uri:
            self.logger.info(
                f"FsF-R1.3-01M : Namespaces included in the metadata -: {list(set(self.fuji.namespace_uri))}"
            )
            for nsuri in list(set(self.fuji.namespace_uri)):
                sinfo = self.get_metadata_standards_info(nsuri, "ns")
                if sinfo:
                    self.found_metadata_standards.append(sinfo)
                    if sinfo.get("type") == "disciplinary":
                        if sinfo.get("name") not in nsstandards:
                            nsstandards.append(sinfo.get("name"))
        if nsstandards:
            self.logger.info(
                "{} : Found metadata standards that are given as namespaces -: {}".format(
                    "FsF-R1.3-01M", str(set(nsstandards))
                )
            )

    def retrieve_metadata_standards_from_sparql(self):
        if self.fuji.sparql_endpoint:
            self.logger.info(
                "{} : Use SPARQL endpoint to retrieve standards used by the repository -: {}".format(
                    "FsF-R1.3-01M", self.fuji.sparql_endpoint
                )
            )
            if self.fuji.uri_validator(self.fuji.sparql_endpoint):
                sparql_provider = SPARQLMetadataProvider(
                    endpoint=self.fuji.sparql_endpoint, logger=self.logger, metric_id="FsF-R1.3-01M"
                )
                standards_uris = sparql_provider.getMetadataStandards()
                self.fuji.namespace_uri.extend(sparql_provider.getNamespaces())
                stds = []
                if standards_uris:
                    for sturi in list(set(standards_uris.values())):
                        sinfo = self.get_metadata_standards_info(sturi, "sparql")
                        if sinfo:
                            self.found_metadata_standards.append(sinfo)
                            if sinfo.get("type") == "disciplinary":
                                stds.append(sinfo.get("name"))
                if stds:
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        "{} : Found metadata standards that are listed in SPARQL endpoint -: {}".format(
                            "FsF-R1.3-01M", str(stds)
                        ),
                    )
            else:
                self.logger.info("{} : Invalid SPARQL endpoint".format("FsF-R1.3-01M"))

    def retrieve_metadata_standards_from_csw(self):
        if self.fuji.csw_endpoint:
            self.logger.info(
                "{} : Use OGC CSW endpoint to retrieve standards used by the repository -: {}".format(
                    "FsF-R1.3-01M", self.fuji.csw_endpoint
                )
            )
            if self.fuji.uri_validator(self.fuji.csw_endpoint):
                csw_provider = OGCCSWMetadataProvider(
                    endpoint=self.fuji.csw_endpoint, logger=self.logger, metric_id="FsF-R1.3-01M"
                )
                standards_uris = csw_provider.getMetadataStandards()
                self.fuji.namespace_uri.extend(csw_provider.getNamespaces())
                stds = []
                if standards_uris:
                    for sturi in list(set(standards_uris.values())):
                        sinfo = self.get_metadata_standards_info(sturi, "csw")
                        if sinfo:
                            self.found_metadata_standards.append(sinfo)
                            if sinfo.get("type") == "disciplinary":
                                stds.append(sinfo.get("name"))
                if stds:
                    self.logger.info(
                        "{} : Found metadata standards that are listed in OGC CSW endpoint -: {}".format(
                            "FsF-R1.3-01M", str(stds)
                        )
                    )
            else:
                self.logger.info("{} : Invalid OGC CSW endpoint".format("FsF-R1.3-01M"))

    def retrieve_metadata_standards_from_oai_pmh(self):
        if self.fuji.oaipmh_endpoint:
            self.logger.info(
                "{} : Use OAI-PMH endpoint to retrieve standards used by the repository -: {}".format(
                    "FsF-R1.3-01M", self.fuji.oaipmh_endpoint
                )
            )
            if self.fuji.uri_validator(self.fuji.oaipmh_endpoint):
                oai_provider = OAIMetadataProvider(
                    endpoint=self.fuji.oaipmh_endpoint, logger=self.logger, metric_id="FsF-R1.3-01M"
                )
                standards_uris = oai_provider.getMetadataStandards()
                self.fuji.namespace_uri.extend(oai_provider.getNamespaces())
                stds = []
                if standards_uris:
                    for sturi in list(set(standards_uris.values())):
                        sinfo = self.get_metadata_standards_info(sturi, "oai-pmh")
                        if sinfo:
                            self.found_metadata_standards.append(sinfo)
                            if sinfo.get("type") == "disciplinary":
                                stds.append(sinfo.get("name"))
                if stds:
                    self.logger.info(
                        "{} : Found metadata standards that are listed in OAI-PMH endpoint -: {}".format(
                            "FsF-R1.3-01M", str(stds)
                        )
                    )
            else:
                self.logger.info("{} : Invalid endpoint".format("FsF-R1.3-01M"))
        else:
            self.logger.warning("{} : NO valid OAI-PMH endpoint found".format("FsF-R1.3-01M"))
        return True

    def retrieve_metadata_standards_from_re3data(self):
        if self.fuji.metadata_merged.get("datacite_client"):
            self.logger.info(
                "FsF-R1.3-01M : Trying to retrieve metadata info from re3data/datacite services using client id -: "
                + str(self.fuji.metadata_merged.get("datacite_client"))
            )
            if self.fuji.pid_scheme:
                repoHelper = self.fuji.repo_helper
                if not self.fuji.metadata_service_url:
                    self.logger.info(
                        "{} : Inferring metadata service endpoint (OAI, SPARQL) information and listed metadata formats through re3data/datacite services".format(
                            "FsF-R1.3-01M"
                        )
                    )
                    self.fuji.oaipmh_endpoint = repoHelper.getRe3MetadataAPIs().get("OAI-PMH")
                    self.fuji.sparql_endpoint = repoHelper.getRe3MetadataAPIs().get("SPARQL")
                    if self.fuji.oaipmh_endpoint or self.fuji.sparql_endpoint:
                        self.logger.info(
                            "{} : Found metadata service endpoint (OAI, SPARQL) listed in re3data record -: {}".format(
                                "FsF-R1.3-01M", (self.fuji.oaipmh_endpoint, self.fuji.sparql_endpoint)
                            )
                        )
                stds = []
                for sturi in repoHelper.getRe3MetadataStandards():
                    sinfo = self.get_metadata_standards_info(sturi, "re3data")
                    # print('OAI URI ', sturi, sinfo)
                    if sinfo:
                        self.found_metadata_standards.append(sinfo)
                        if sinfo.get("name") not in stds:
                            stds.append(sinfo.get("name"))
                self.logger.info(
                    "{} : Metadata standards listed in re3data record -: {}".format("FsF-R1.3-01M", str(stds))
                )
        else:
            self.logger.info(
                "FsF-R1.3-01M : No Datacite client id found, therefore skipping re3data metadata retrieval"
            )
            # verify the service url by domain matching
        self.validate_service_url()

    def retrieve_metadata_standards_from_apis(self):
        if self.fuji.landing_url is not None:
            self.logger.info("FsF-R1.3-01M : Retrieving API and Standards")
            if self.fuji.metadata_service_url not in [None, ""]:
                self.logger.info(
                    "FsF-R1.3-01M : Metadata service endpoint ("
                    + str(self.fuji.metadata_service_type)
                    + ") provided as part of the assessment request -: "
                    + str(self.fuji.metadata_service_url)
                )
            self.retrieve_metadata_standards_from_re3data()
            # retrieve metadata standards info from oai-pmh
            self.retrieve_metadata_standards_from_oai_pmh()
            # retrieve metadata standards info from OGC CSW
            self.retrieve_metadata_standards_from_csw()
            # retrieve metadata standards info from SPARQL endpoint
            self.retrieve_metadata_standards_from_sparql()
        else:
            self.logger.warning(
                "{} : Skipped external ressources (e.g. OAI, re3data) checks since landing page could not be resolved".format(
                    "FsF-R1.3-01M"
                )
            )

    def filter_community_metadata_standards(self, testid, found_metadata_standards):
        test_requirements = []
        if self.metric_tests[self.metric_identifier + str(testid)].metric_test_requirements:
            test_requirements = self.metric_tests[self.metric_identifier + str(testid)].metric_test_requirements[0]
        if test_requirements:
            community_standards = []
            if test_requirements.get("required"):
                test_required = []
                if isinstance(test_requirements.get("required"), list):
                    test_required = test_requirements.get("required")
                elif test_requirements.get("required").get("name"):
                    test_required = test_requirements.get("required").get("name")
                if not isinstance(test_required, list):
                    test_required = [test_required]
                if test_required:
                    self.logger.info(
                        "{0} : Will exclusively consider community specific metadata standards for {0}{1} which are specified in metrics -: {2}".format(
                            self.metric_identifier, str(testid), test_required
                        )
                    )
                    for rq_mstandard_id in list(test_required):
                        for kn_mstandard in found_metadata_standards:
                            # check if internal or external identifiers (RDA, fairsharing) are listed
                            if rq_mstandard_id in kn_mstandard.get(
                                "external_ids"
                            ) or rq_mstandard_id == kn_mstandard.get("id"):
                                community_standards.append(kn_mstandard.get("id"))
                    if len(community_standards) > 0:
                        self.logger.info(
                            "{} : Identifiers of community specific metadata standards found -: {}".format(
                                self.metric_identifier, community_standards
                            )
                        )
                    found_metadata_standards = [
                        x for x in found_metadata_standards if x.get("id") in community_standards
                    ]
        return found_metadata_standards

    def testMultidisciplinarybutCommunityEndorsedMetadataDetected(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-3"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-3")
            generic_found = False
            found_metadata_standards = self.filter_community_metadata_standards("-3", self.found_metadata_standards)
            for found_standard in found_metadata_standards:
                if found_standard.get("type") == "generic":
                    generic_found = True
                    if found_standard not in self.valid_metadata_standards:
                        self.valid_metadata_standards.append(found_standard)
            if generic_found:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    "FsF-R1.3-01M : Found non-disciplinary standards (but RDA listed) using namespaces or schemas found in re3data record or via provided metadata or metadata services outputs",
                )
                self.setEvaluationCriteriumScore(self.metric_identifier + "-3", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-3").metric_test_maturity_config
                self.score.earned = test_score
                test_status = True
        return test_status

    def testCommunitySpecificMetadataDetectedviaRe3Data(self):
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            specific_found = False
            found_metadata_standards = self.filter_community_metadata_standards("-2", self.found_metadata_standards)
            for found_standard in found_metadata_standards:
                if found_standard.get("type") == "disciplinary" and found_standard.get("source") == "re3data":
                    specific_found = True
                    if found_standard not in self.valid_metadata_standards:
                        self.valid_metadata_standards.append(found_standard)
            if specific_found:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    "FsF-R1.3-01M : Found disciplinary standard listed in the re3data record of the responsible repository",
                )
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-2").metric_test_maturity_config
                self.score.earned = test_score
                return True
        else:
            return False

    def testCommunitySpecificMetadataDetectedviaNamespaces(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            specific_found = False
            found_metadata_standards = self.filter_community_metadata_standards("-1", self.found_metadata_standards)
            for found_standard in found_metadata_standards:
                if found_standard.get("type") == "disciplinary" and found_standard.get("source") != "re3data":
                    specific_found = True
                    if found_standard not in self.valid_metadata_standards:
                        self.valid_metadata_standards.append(found_standard)
            if specific_found:
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    "FsF-R1.3-01M : Found disciplinary standard using namespaces or schemas found in provided metadata or metadata services outputs ",
                )
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                self.maturity = self.metric_tests.get(self.metric_identifier + "-1").metric_test_maturity_config
                self.score.earned = test_score
                test_status = True
        return test_status

    def get_metadata_standards_info(self, uri, source):
        standard_found = self.fuji.metadata_harvester.lookup_metadatastandard_by_uri(uri)
        if standard_found:
            metadata_info = self.fuji.metadata_harvester.get_metadata_standard_info(standard_found)
            if metadata_info.get("type") == "generic":
                self.logger.info(
                    "FsF-R1.3-01M : Found non-disciplinary standard (but RDA listed) -: via {}:  {} - {}".format(
                        str(source), metadata_info.get("name"), uri
                    )
                )
            else:
                self.logger.info(
                    "FsF-R1.3-01M : Found disciplinary standard -: via {} : {} - {}".format(
                        str(source), metadata_info.get("name"), uri
                    )
                )
            metadata_info["uri"] = uri
            metadata_info["source"] = source
            return metadata_info
        else:
            return {}

    def evaluate(self):
        self.community_standards_output: list[CommunityEndorsedStandardOutputInner] = []

        self.retrieve_metadata_standards_from_namespaces()
        self.retrieve_metadata_standards_from_apis()

        self.result = CommunityEndorsedStandard(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )

        if self.testMultidisciplinarybutCommunityEndorsedMetadataDetected():
            self.result.test_status = "pass"
        if self.testCommunitySpecificMetadataDetectedviaRe3Data():
            self.result.test_status = "pass"
        if self.testCommunitySpecificMetadataDetectedviaNamespaces():
            self.result.test_status = "pass"
        for found_standard in self.valid_metadata_standards:
            out = CommunityEndorsedStandardOutputInner()
            out.metadata_standard = found_standard.get("name")  # use here original standard uri detected
            out.subject_areas = found_standard.get("subject")
            out.url = found_standard.get("uri")
            out.type = found_standard.get("type")
            out.source = found_standard.get("catalogue")
            self.community_standards_output.append(out)
        if not self.community_standards_output:
            self.logger.warning("FsF-R1.3-01M : Unable to determine community standard(s)")
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.output = self.community_standards_output
