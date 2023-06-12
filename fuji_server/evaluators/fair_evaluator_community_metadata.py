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

from typing import List
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_provider_csw import OGCCSWMetadataProvider
from fuji_server.helper.metadata_provider_oai import OAIMetadataProvider
from fuji_server.helper.metadata_provider_sparql import SPARQLMetadataProvider
from fuji_server.helper.repository_helper import RepositoryHelper
from fuji_server.models.community_endorsed_standard import CommunityEndorsedStandard
from fuji_server.models.community_endorsed_standard_output_inner import CommunityEndorsedStandardOutputInner
from tldextract import extract

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
        self.set_metric('FsF-R1.3-01M')
        self.multidiscipliary_standards_detected = []
        self.community_standards_detected = []
        self.community_standards_uri = {}
        self.community_standards = []
        self.found_metadata_standards = []

    def validate_service_url(self):
        # checks if service url and landing page url have same domain in order to avoid manipulations
        if self.fuji.metadata_service_url:
            service_url_parts = extract(self.fuji.metadata_service_url)
            landing_url_parts = extract(self.fuji.landing_url)
            service_domain = service_url_parts.domain + '.' + service_url_parts.suffix
            landing_domain = landing_url_parts.domain + '.' + landing_url_parts.suffix
            if landing_domain == service_domain:
                return True
            else:
                self.logger.warning(
                    'FsF-R1.3-01M : Service URL domain/subdomain does not match with landing page domain -: {}'.format(
                        service_domain, landing_domain))
                self.fuji.metadata_service_url, self.fuji.csw_endpoint, self.fuji.oaipmh_endpoint, self.fuji.sparql_endpoint = None, None, None, None
                return False
        else:
            return False

    def retrieve_metadata_standards_from_namespaces(self):
        nsstandards = []
        if self.fuji.namespace_uri:
            self.logger.info('FsF-R1.3-01M : Namespaces included in the metadata -: {}'.format(self.fuji.namespace_uri))
            for nsuri in self.fuji.namespace_uri:
                sinfo = self.get_metadata_standards_info(nsuri , 'ns')
            if sinfo:
                self.found_metadata_standards.append(sinfo)
                nsstandards.append(sinfo.get('name'))
        if nsstandards:
            self.logger.log(
                self.fuji.LOG_SUCCESS,
                '{} : Found disciplinary standards that are given as namespaces -: {}'.format(
                    'FsF-R1.3-01M', str(set(nsstandards))))

    def retrieve_metadata_standards_from_sparql(self):
        if self.fuji.sparql_endpoint:
            self.logger.info('{} : Use SPARQL endpoint to retrieve standards used by the repository -: {}'.format(
                'FsF-R1.3-01M', self.fuji.sparql_endpoint))
            if self.fuji.uri_validator(self.fuji.sparql_endpoint):
                sparql_provider = SPARQLMetadataProvider(endpoint=self.fuji.sparql_endpoint,
                                                         logger=self.logger,
                                                         metric_id='FsF-R1.3-01M')
                standards_uris = sparql_provider.getMetadataStandards()
                self.fuji.namespace_uri.extend(sparql_provider.getNamespaces())
                stds = None
                if standards_uris:
                    for sturi in standards_uris.values():
                        sinfo = self.get_metadata_standards_info(sturi, 'sparql')
                        if sinfo:
                            self.found_metadata_standards.append(sinfo)
                    stds = list(self.community_standards_uri.keys())
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        '{} : Found disciplinary standards that are listed in SPARQL endpoint -: {}'.format(
                            'FsF-R1.3-01M', stds))
            else:
                self.logger.info('{} : Invalid SPARQL endpoint'.format('FsF-R1.3-01M'))

    def retrieve_metadata_standards_from_csw(self):
        if self.fuji.csw_endpoint:
            self.logger.info('{} : Use OGC CSW endpoint to retrieve standards used by the repository -: {}'.format(
                'FsF-R1.3-01M', self.fuji.csw_endpoint))
            if (self.fuji.uri_validator(self.fuji.csw_endpoint)):
                csw_provider = OGCCSWMetadataProvider(endpoint=self.fuji.csw_endpoint,
                                                      logger=self.logger,
                                                      metric_id='FsF-R1.3-01M')
                standards_uris = csw_provider.getMetadataStandards()
                self.fuji.namespace_uri.extend(csw_provider.getNamespaces())
                stds = None
                if standards_uris:
                    for sturi in standards_uris.values():
                        sinfo = self.get_metadata_standards_info(sturi, 'csw')
                        if sinfo:
                            self.found_metadata_standards.append(sinfo)
                if standards_uris:
                    stds = list(self.community_standards_uri.keys())
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        '{} : Found disciplinary standards that are listed in OGC CSW endpoint -: {}'.format(
                            'FsF-R1.3-01M', stds))
            else:
                self.logger.info('{} : Invalid OGC CSW endpoint'.format('FsF-R1.3-01M'))

    def retrieve_metadata_standards_from_oai_pmh(self):
        if self.fuji.oaipmh_endpoint:
            self.logger.info('{} : Use OAI-PMH endpoint to retrieve standards used by the repository -: {}'.format(
                'FsF-R1.3-01M', self.fuji.oaipmh_endpoint))
            if (self.fuji.uri_validator(self.fuji.oaipmh_endpoint)):
                oai_provider = OAIMetadataProvider(endpoint=self.fuji.oaipmh_endpoint,
                                                   logger=self.logger,
                                                   metric_id='FsF-R1.3-01M')
                standards_uris = oai_provider.getMetadataStandards()
                self.fuji.namespace_uri.extend(oai_provider.getNamespaces())
                stds = None
                if standards_uris:
                    for sturi in standards_uris.values():
                        sinfo = self.get_metadata_standards_info(sturi, 'oai-pmh')
                        if sinfo:
                            self.found_metadata_standards.append(sinfo)
                    stds = list(standards_uris.keys())
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        '{} : Found disciplinary standards that are listed in OAI-PMH endpoint -: {}'.format(
                            'FsF-R1.3-01M', stds))
            else:
                self.logger.info('{} : Invalid endpoint'.format('FsF-R1.3-01M'))
        else:
            self.logger.warning('{} : NO valid OAI-PMH endpoint found'.format('FsF-R1.3-01M'))
        return True

    def retrieve_metadata_standards_from_re3data(self):
        if self.fuji.use_datacite:
            if self.fuji.use_datacite:
                client_id = self.fuji.metadata_merged.get('datacite_client')
                self.logger.info('FsF-R1.3-01M : re3data/datacite client id -: {}'.format(client_id))
            else:
                client_id = None
                self.logger.warning(
                    '{} : Datacite support disabled, therefore skipping standards identification using in re3data record'
                    .format(
                        'FsF-R1.3-01M',
                    ))
            self.logger.info(
                'FsF-R1.3-01M : Trying to retrieve metadata info from re3data/datacite services using client id -: '
                + str(client_id))
            if client_id and self.fuji.pid_scheme:
                repoHelper = RepositoryHelper(client_id, self.fuji.pid_scheme, logger=self.logger.name,
                                              landingpage=self.fuji.landing_url)
                repoHelper.lookup_re3data()
                if not self.fuji.metadata_service_url:
                    self.logger.info('{} : Inferring metadata service endpoint (OAI, SPARQL) information through re3data/datacite services'.format(
                        'FsF-R1.3-01M'))
                    self.fuji.oaipmh_endpoint = repoHelper.getRe3MetadataAPIs().get('OAI-PMH')
                    self.fuji.sparql_endpoint = repoHelper.getRe3MetadataAPIs().get('SPARQL')
                    for sturi in repoHelper.getRe3MetadataStandards():
                        sinfo = self.get_metadata_standards_info(sturi, 're3data')
                        if sinfo:
                            self.found_metadata_standards.append(sinfo)
                self.community_standards.extend(repoHelper.getRe3MetadataStandards())
                self.logger.info('{} : Metadata standards listed in re3data record -: {}'.format(
                    'FsF-R1.3-01M', self.community_standards))
        else:
            self.logger.info(
                'FsF-R1.3-01M : Skipped re3data metadata standards query since Datacite support is disabled by user'
            )
            # verify the service url by domain matching
        self.validate_service_url()

    def retrieve_apis_standards(self):
        if self.fuji.landing_url is not None:
            self.logger.info('FsF-R1.3-01M : Retrieving API and Standards')
            if self.fuji.metadata_service_url not in [None, '']:
                self.logger.info('FsF-R1.3-01M : Metadata service endpoint (' + str(self.fuji.metadata_service_type) +
                                 ') provided as part of the assessment request -: ' + str(self.fuji.metadata_service_url))
            self.retrieve_metadata_standards_from_re3data()
            # retrieve metadata standards info from oai-pmh
            self.retrieve_metadata_standards_from_oai_pmh()
            # retrieve metadata standards info from OGC CSW
            self.retrieve_metadata_standards_from_csw()
            # retrieve metadata standards info from SPARQL endpoint
            self.retrieve_metadata_standards_from_sparql()
        else:
            self.logger.warning(
                '{} : Skipped external ressources (e.g. OAI, re3data) checks since landing page could not be resolved'.
                format('FsF-R1.3-01M'))

    def testMultidisciplinarybutCommunityEndorsedMetadataDetected(self):
        if self.isTestDefined(self.metric_identifier + '-3'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-3')
            generic_found = False
            for found_standard in self.found_metadata_standards:

                if found_standard.get('type')=='generic':
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                    'FsF-R1.3-01M : Found non-disciplinary standard (but RDA listed) using namespaces or schemas found in re3data record or via provided metadata or metadata services outputs -: {}'
                    .format(str(found_standard.get('name')) + ' (' + str(found_standard.get('uri')) + ')'))
                    generic_found = True
            if generic_found:
                self.setEvaluationCriteriumScore(self.metric_identifier + '-3', test_score, 'pass')
                self.maturity = self.metric_tests.get(self.metric_identifier + '-3').metric_test_maturity_config
                self.score.earned = test_score
                return True
        else:
            return False

    def testCommunitySpecificMetadataDetectedviaRe3Data(self):
        if self.isTestDefined(self.metric_identifier + '-3'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-2')
            specific_found = False
            for found_standard in self.found_metadata_standards:

                if found_standard.get('type') == 'disciplinary':
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        'FsF-R1.3-01M : Found disciplinary standard listed in the re3data record of the responsible repository -: {}'
                            .format(str(found_standard.get('name')) + ' (' + str(found_standard.get('uri')) + ')'))
                    specific_found = True
            if specific_found:
                self.setEvaluationCriteriumScore(self.metric_identifier + '-2', test_score, 'pass')
                self.maturity = self.metric_tests.get(self.metric_identifier + '-2').metric_test_maturity_config
                self.score.earned = test_score
                return True
        else:
            return False

    def testCommunitySpecificMetadataDetectedviaNamespaces(self):
        if self.isTestDefined(self.metric_identifier + '-1'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-1')
            specific_found = False
            for found_standard in self.found_metadata_standards:

                if found_standard.get('type') == 'disciplinary':
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        'FsF-R1.3-01M : Found disciplinary standard using namespaces or schemas found in provided metadata or metadata services outputs -: {}'
                            .format(str(found_standard.get('name')) + ' (' + str(found_standard.get('uri')) + ')'))
                    specific_found = True
            if specific_found:
                self.setEvaluationCriteriumScore(self.metric_identifier + '-1', test_score, 'pass')
                self.maturity = self.metric_tests.get(self.metric_identifier + '-1').metric_test_maturity_config
                self.score.earned = test_score
                return True
        else:
            return False

    def get_metadata_standards_info(self, uri, source):
        standard_found = self.fuji.lookup_metadatastandard_by_uri(uri)
        type = None
        if standard_found:
            subject = self.fuji.COMMUNITY_METADATA_STANDARDS_URIS.get(standard_found).get('field_of_science')
            std_name = self.fuji.COMMUNITY_METADATA_STANDARDS_URIS.get(standard_found).get('title')
            if subject:
                if subject == ['sciences'] or all(elem == 'Multidisciplinary' for elem in subject):
                    self.multidiscipliary_standards_detected.append(std_name)
                    self.logger.info(
                        'FsF-R1.3-01M : Found non-disciplinary standard (but RDA listed) -: via {}:  {}'
                            .format(str(source),std_name))
                    type = 'generic'
                else:
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        'FsF-R1.3-01M : Found disciplinary standard -: via {}:{}'.format(str(source),std_name))
                    type = 'disciplinary'
                out = CommunityEndorsedStandardOutputInner()
                out.metadata_standard = std_name  # use here original standard uri detected
                out.subject_areas = subject
                out.urls = [standard_found]
                self.community_standards_detected.append(out)
            return {'subject': subject, 'name': std_name, 'type':type, 'source':source, 'uri':uri}
        else:
            return {}


    def evaluate(self):
        self.retrieve_metadata_standards_from_namespaces()
        self.retrieve_apis_standards()

        self.result = CommunityEndorsedStandard(id=self.metric_number,
                                                metric_identifier=self.metric_identifier,
                                                metric_name=self.metric_name)

        self.community_standards_detected: List[CommunityEndorsedStandardOutputInner] = []

        if self.testMultidisciplinarybutCommunityEndorsedMetadataDetected():
            self.community_standards_detected = False
            self.result.test_status = 'pass'
        if self.testCommunitySpecificMetadataDetectedviaRe3Data():
            self.community_standards_detected = True
            self.result.test_status = 'pass'
        if self.testCommunitySpecificMetadataDetectedviaNamespaces():
            self.community_standards_detected = True
            self.result.test_status = 'pass'

        if not self.community_standards_detected:
            self.logger.warning('FsF-R1.3-01M : Unable to determine community standard(s)')
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.output = self.community_standards_detected
