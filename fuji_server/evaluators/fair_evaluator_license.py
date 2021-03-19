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
import Levenshtein

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.license import License
from fuji_server.models.license_output import LicenseOutput
from fuji_server.models.license_output_inner import LicenseOutputInner
import idutils
from fuji_server.helper.metadata_mapper import Mapper

class FAIREvaluatorLicense(FAIREvaluator):

    def isLicense (self, value, metric_id):
        islicense = False
        isurl = idutils.is_url(value)
        spdx_html = None
        spdx_osi = None
        if isurl:
            spdx_html, spdx_osi = self.lookup_license_by_url(value, metric_id)
        else:
            spdx_html, spdx_osi = self.lookup_license_by_name(value, metric_id)
        if spdx_html or spdx_osi:
            islicense = True
        return islicense

    def lookup_license_by_url(self, u, metric_id):
        self.logger.info('{0} : Verify URL through SPDX registry -: {1}'.format(metric_id, u))
        html_url = None
        isOsiApproved = False
        for item in self.fuji.SPDX_LICENSES:
            # u = u.lower()
            # if any(u in v.lower() for v in item.values()):
            seeAlso = item['seeAlso']
            if any(u in v for v in seeAlso):
                self.logger.info('{0} : Found SPDX license representation -: {1}'.format(metric_id, item['detailsUrl']))
                # html_url = '.html'.join(item['detailsUrl'].rsplit('.json', 1))
                html_url = item['detailsUrl'].replace(".json", ".html")
                isOsiApproved = item['isOsiApproved']
                break
        return html_url, isOsiApproved

    def lookup_license_by_name(self, lvalue, metric_id):
        # TODO - find simpler way to run fuzzy-based search over dict/json (e.g., regex)
        html_url = None
        isOsiApproved = False
        self.logger.info('{0} : Verify name through SPDX registry -: {1}'.format(metric_id, lvalue))
        # Levenshtein distance similarity ratio between two license name
        sim = [Levenshtein.ratio(lvalue.lower(), i) for i in self.fuji.SPDX_LICENSE_NAMES]
        if max(sim) > 0.85:
            index_max = max(range(len(sim)), key=sim.__getitem__)
            sim_license = self.fuji.SPDX_LICENSE_NAMES[index_max]
            found = next((item for item in self.fuji.SPDX_LICENSES if item['name'] == sim_license), None)
            self.logger.info('{0}: Found SPDX license representation -: {1}'.format(metric_id,found['detailsUrl']))
            # html_url = '.html'.join(found['detailsUrl'].rsplit('.json', 1))
            html_url = found['detailsUrl'].replace(".json", ".html")
            isOsiApproved = found['isOsiApproved']
        return html_url, isOsiApproved

    def evaluate(self):

        self.result = License(id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        licenses_list = []
        specified_licenses = self.fuji.metadata_merged.get('license')
        self.score.earned = 0
        spdx_found = False
        if specified_licenses is not None and specified_licenses !=[]:
            self.logger.log(self.fuji.LOG_SUCCESS, '{0} : Found licence information in metadata'.format(self.metric_identifier))
            if isinstance(specified_licenses, str):  # licenses maybe string or list depending on metadata schemas
                specified_licenses = [specified_licenses]
            for l in specified_licenses:
                license_output = LicenseOutputInner()
                #license can be dict or
                license_output.license = l
                if isinstance(l, str):
                    isurl = idutils.is_url(l)
                if isurl:
                    spdx_html, spdx_osi = self.lookup_license_by_url(l, self.metric_identifier)
                else:  # maybe licence name
                    spdx_html, spdx_osi = self.lookup_license_by_name(l, self.metric_identifier)
                if not spdx_html:
                    self.logger.warning('{0} : NO SPDX license representation (spdx url, osi_approved) found'.format(self.metric_identifier))
                else:
                    self.logger.log(self.fuji.LOG_SUCCESS, '{0} : Found SPDX license representation (spdx url, osi_approved)'.format(self.metric_identifier))
                    spdx_found = True
                license_output.details_url = spdx_html
                license_output.osi_approved = spdx_osi
                licenses_list.append(license_output)
            self.result.test_status = "pass"
            self.setEvaluationCriteriumScore('FsF-R1.1-01M-1', 1, 'pass')
            self.score.earned = 1
            self.maturity = 2
            if spdx_found:
                self.setEvaluationCriteriumScore('FsF-R1.1-01M-2', 1, 'pass')
                self.score.earned = 2
                self.maturity = 3
        else:
            self.logger.warning('{0} : License information unavailable in metadata'.format(self.metric_identifier))

        self.result.output = licenses_list
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity_levels.get(self.maturity)

