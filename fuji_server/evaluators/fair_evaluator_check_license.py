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

    def evaluate(self):

        self.result = License(id=self.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        licenses_list = []
        specified_licenses = self.fuji.metadata_merged.get('license')

        if specified_licenses is not None and specified_licenses !=[]:
            if isinstance(specified_licenses, str):  # licenses maybe string or list depending on metadata schemas
                specified_licenses = [specified_licenses]
            for l in specified_licenses:
                license_output = LicenseOutputInner()
                #license can be dict or
                license_output.license = l
                if isinstance(l, str):
                    isurl = idutils.is_url(l)
                if isurl:
                    spdx_html, spdx_osi = self.fuji.lookup_license_by_url(l, self.metric_identifier)
                else:  # maybe licence name
                    spdx_html, spdx_osi = self.fuji.lookup_license_by_name(l, self.metric_identifier)
                if not spdx_html:
                    self.logger.warning('FsF-R1.1-01M : NO SPDX license representation (spdx url, osi_approved) found')
                license_output.details_url = spdx_html
                license_output.osi_approved = spdx_osi
                licenses_list.append(license_output)
            self.result.test_status = "pass"
            self.score.earned = self.total_score
        else:
            self.score.earned = 0
            self.logger.warning('FsF-R1.1-01M : License unavailable')

        self.result.output = licenses_list
        self.result.score = self.score
