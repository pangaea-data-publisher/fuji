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
import fnmatch
import re
import urllib.parse

import Levenshtein
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.fair_result_evaluation_criterium_requirements import FAIRResultEvaluationCriteriumRequirements
from fuji_server.models.license import License
from fuji_server.models.license_output_inner import LicenseOutputInner
import idutils


class FAIREvaluatorLicense(FAIREvaluator):
    """
    A class to evaluate the license information under which data can be reused (R1.1-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate metadata information about license that is represented by
        using an appropriate metadata element and machine readable license

    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric('FsF-R1.1-01M')

        self.output=[]
        self.license_info =[]

    def setLicenseDataAndOutput(self):
        self.license_info = []
        specified_licenses = self.fuji.metadata_merged.get('license')
        if isinstance(specified_licenses, str):  # licenses maybe string or list depending on metadata schemas
            specified_licenses = [specified_licenses]
        if specified_licenses is not None and specified_licenses != []:
            for l in specified_licenses:
                licence_valid = False
                license_output = LicenseOutputInner()
                if isinstance(l, str):
                    isurl = idutils.is_url(l)
                if isurl:
                    iscc, generic_cc = self.isCreativeCommonsLicense(l, self.metric_identifier)
                    if iscc:
                        l = generic_cc
                    spdx_uri, spdx_osi, spdx_id = self.lookup_license_by_url(l, self.metric_identifier)
                else:  # maybe licence name
                    spdx_uri, spdx_osi, spdx_id = self.lookup_license_by_name(l, self.metric_identifier)
                license_output.license = l
                if spdx_uri:
                    licence_valid = True
                license_output.details_url = spdx_uri
                license_output.osi_approved = spdx_osi
                self.output.append((license_output))
                self.license_info.append({'license':l, 'id': spdx_id, 'is_url': isurl, 'spdx_uri':spdx_uri , 'osi_approved':spdx_osi, 'valid':licence_valid})
                if not spdx_uri:
                    self.logger.warning('{0} : NO SPDX license representation (spdx url, osi_approved) found'.format(
                        self.metric_identifier))
                else:
                    test_status = True
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        '{0} : Found SPDX license representation (spdx url, osi_approved)'.format(
                            self.metric_identifier))


    def isCreativeCommonsLicense(self,license_url, metric_id):
        iscc = False
        genericcc = None
        try:
            #https://wiki.creativecommons.org/wiki/License_Properties
            ccregex= r'https?://creativecommons\.org/licenses/(by(-nc)?(-nd)?(-sa)?)/(1\.0|2\.0|2\.5|3\.0|4\.0)'
            ccmatch = re.match(ccregex, license_url)
            if ccmatch:
                self.logger.info('{0} : Found CreativeCommons license -: {1}'.format(metric_id, license_url))
                genericcc = ccmatch[0]
                iscc = True
            else:
                iscc =  False
        except Exception as e:
            iscc =  False
        return iscc, genericcc

    def isLicense(self, value, metric_id):
        islicense = False
        isurl = idutils.is_url(value)
        spdx_html = None
        spdx_osi = None
        if isurl:
            iscc, generic_cc = self.isCreativeCommonsLicense(value, metric_id)
            if iscc:
                l = generic_cc
            spdx_html, spdx_osi, spdx_id = self.lookup_license_by_url(value, metric_id)
        else:
            spdx_html, spdx_osi, spdx_id = self.lookup_license_by_name(value, metric_id)
        if spdx_html or spdx_osi:
            islicense = True
        return islicense

    def lookup_license_by_url(self, u, metric_id):
        self.logger.info('{0} : Verify URL through SPDX registry -: {1}'.format(metric_id, u))
        html_url = None
        isOsiApproved = False
        id = None
        ul = None
        if 'spdx.org/licenses' in u:
            ul = u.split('/')[-1]
        for item in self.fuji.SPDX_LICENSES:
            # u = u.lower()
            # if any(u in v.lower() for v in item.values()):
            licenseId = item.get('licenseId')
            seeAlso = item.get('seeAlso')
            if any(u in v for v in seeAlso) or licenseId == ul:
                self.logger.info('{0} : Found SPDX license representation -: {1}'.format(metric_id, item['detailsUrl']))
                # html_url = '.html'.join(item['detailsUrl'].rsplit('.json', 1))
                html_url = item['detailsUrl'].replace('.json', '.html')
                isOsiApproved = item['isOsiApproved']
                id = item['licenseId']
                break
        return html_url, isOsiApproved, id

    def lookup_license_by_name(self, lvalue, metric_id):
        # TODO - find simpler way to run fuzzy-based search over dict/json (e.g., regex)
        html_url = None
        isOsiApproved = False
        id = None
        self.logger.info('{0} : Verify name through SPDX registry -: {1}'.format(metric_id, lvalue))
        # Levenshtein distance similarity ratio between two license name
        if lvalue:
            sim = [Levenshtein.ratio(lvalue.lower(), i) for i in self.fuji.SPDX_LICENSE_NAMES]
            if max(sim) > 0.85:
                index_max = max(range(len(sim)), key=sim.__getitem__)
                sim_license = self.fuji.SPDX_LICENSE_NAMES[index_max]
                found = next((item for item in self.fuji.SPDX_LICENSES if item['name'] == sim_license), None)
                self.logger.info('{0}: Found SPDX license representation -: {1}'.format(metric_id, found['detailsUrl']))
                # html_url = '.html'.join(found['detailsUrl'].rsplit('.json', 1))
                html_url = found['detailsUrl'].replace('.json', '.html')
                isOsiApproved = found['isOsiApproved']
                id = found['licenseId']
        return html_url, isOsiApproved, id

    def testLicenseMetadataElementAvailable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-1'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-1')
            if self.license_info is not None and self.license_info  != []:
                test_status = True
                self.logger.log(self.fuji.LOG_SUCCESS,
                                '{0} : Found licence information in metadata'.format(self.metric_identifier))
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + '-1')
                self.setEvaluationCriteriumScore(self.metric_identifier + '-1', test_score, 'pass')
                self.score.earned += test_score
            else:
                self.logger.warning('{0} : License information unavailable in metadata'.format(self.metric_identifier))
        return test_status

    def testLicenseIsValidAndSPDXRegistered(self):
        test_status = False
        test_requirements = {}
        if self.isTestDefined(self.metric_identifier + '-2'):
            if self.metric_tests[self.metric_identifier + '-2'].metric_test_requirements:
                test_requirements = self.metric_tests[self.metric_identifier + '-2'].metric_test_requirements[0]
            test_score = self.getTestConfigScore(self.metric_identifier + '-2')
            if test_requirements.get('required'):
                self.logger.info(
                    '{0} : Will exclusively consider community specific licenses for {0}{1} which are specified in metrics -: {2}'.format(
                        self.metric_identifier, '-2', test_requirements.get('required')))
            else:
                self.logger.info(
                    '{0} : Will consider all SPDX licenses as community specific licenses for {0} '.format(
                        self.metric_identifier, '-2'))
            if self.license_info:
                for l in self.license_info:
                    if test_requirements.get('required'):
                        for rq_license_id in list(test_requirements.get('required')):
                            if fnmatch.fnmatch(l.get('id'), rq_license_id):
                                test_status = True
                    else:
                        if l.get('valid'):
                            test_status = True
            else:
                self.logger.warning('{0} : Skipping SPDX and community license verification since license information unavailable in metadata'.format(self.metric_identifier))

            if test_status:
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + '-2')
                self.score.earned += test_score
                self.setEvaluationCriteriumScore(self.metric_identifier + '-2', test_score, 'pass')

        return test_status

    def evaluate(self):

        self.setLicenseDataAndOutput()

        self.result = License(id=self.metric_number,
                              metric_identifier=self.metric_identifier,
                              metric_name=self.metric_name)

        license_status = 'fail'
        if self.testLicenseMetadataElementAvailable():
            license_status = 'pass'
        if self.testLicenseIsValidAndSPDXRegistered():
            license_status = 'pass'

        self.result.test_status = license_status
        self.result.output = self.output
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
