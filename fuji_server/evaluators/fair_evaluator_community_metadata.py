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

    def evaluate(self):
        self.result = CommunityEndorsedStandard(id=self.metric_number,
                                                metric_identifier=self.metric_identifier,
                                                metric_name=self.metric_name)

        community_standards_detected: List[CommunityEndorsedStandardOutputInner] = []
        multidiscipliary_standards_detected = []
        if self.fuji.namespace_uri:
            self.fuji.namespace_uri = list(set(self.fuji.namespace_uri))
        # ============== retrieve community standards by collected namespace uris
        if len(self.fuji.namespace_uri) > 0:
            no_match = []
            self.logger.info('FsF-R1.3-01M : Namespaces included in the metadata -: {}'.format(self.fuji.namespace_uri))
            for std_ns in self.fuji.namespace_uri:
                std_ns_temp = self.fuji.lookup_metadatastandard_by_uri(std_ns)
                # if std_ns_temp in FAIRCheck.COMMUNITY_METADATA_STANDARDS_URIS:
                if std_ns_temp:
                    subject = self.fuji.COMMUNITY_METADATA_STANDARDS_URIS.get(std_ns_temp).get('field_of_science')
                    std_name = self.fuji.COMMUNITY_METADATA_STANDARDS_URIS.get(std_ns_temp).get('title')
                    if subject:
                        if all(elem == 'Multidisciplinary' for elem in subject):
                            self.logger.info(
                                'FsF-R1.3-01M : Found non-disciplinary standard (but RDA listed) found through namespaces -: {}'
                                .format(str(std_name) + ' (' + str(std_ns) + ')'))
                            self.setEvaluationCriteriumScore('FsF-R1.3-01M-3', 0, 'pass')
                            self.maturity = 1
                            multidiscipliary_standards_detected.append(std_name)
                        else:
                            self.logger.log(
                                self.fuji.LOG_SUCCESS,
                                'FsF-R1.3-01M : Found disciplinary standard through namespaces -: {}'.format(std_ns))
                        nsout = CommunityEndorsedStandardOutputInner()
                        nsout.metadata_standard = std_name  # use here original standard uri detected
                        nsout.subject_areas = subject
                        nsout.urls = [std_ns]
                        community_standards_detected.append(nsout)
                else:
                    no_match.append(std_ns)
            if len(no_match) > 0:
                self.logger.info(
                    'FsF-R1.3-01M : The following standards found through namespaces are excluded as they are not listed in RDA metadata catalog -: {}'
                    .format(no_match))
        if len(community_standards_detected) - len(multidiscipliary_standards_detected) > 0:
            self.maturity = 3
            self.setEvaluationCriteriumScore('FsF-R1.3-01M-1', 1, 'pass')

        # ============== use standards listed in the re3data record if no metadata is detected from oai-pmh
        re3_detected = False
        if len(self.fuji.community_standards) > 0:
            #if len(community_standards_detected) == 0:
            if self.fuji.use_datacite:
                self.logger.info('FsF-R1.3-01M : Using re3data to detect metadata standard(s)')
                for s in self.fuji.community_standards:
                    standard_found = self.fuji.lookup_metadatastandard_by_uri(s)
                    if standard_found:
                        subject = self.fuji.COMMUNITY_METADATA_STANDARDS_URIS.get(s).get('field_of_science')
                        std_name = self.fuji.COMMUNITY_METADATA_STANDARDS_URIS.get(s).get('title')
                        if subject:
                            if subject == ['sciences']:
                                self.logger.info(
                                    'FsF-R1.3-01M : Found non-disciplinary standard (but RDA listed) found through re3data -: {}'
                                    .format(std_name))
                                self.setEvaluationCriteriumScore('FsF-R1.3-01M-3', 0, 'pass')
                                if self.maturity <= 1:
                                    self.maturity = 1
                                multidiscipliary_standards_detected.append(std_name)
                            else:
                                if self.maturity < 2:
                                    self.maturity = 2
                                re3_detected = True
                                self.logger.log(
                                    self.fuji.LOG_SUCCESS,
                                    'FsF-R1.3-01M : Found disciplinary standard through re3data -: {}'.format(std_name))
                            out = CommunityEndorsedStandardOutputInner()
                            out.metadata_standard = std_name  # use here original standard uri detected
                            out.subject_areas = subject
                            out.urls = [standard_found]
                            community_standards_detected.append(out)

            elif self.fuji.use_datacite:
                self.logger.info(
                    'FsF-R1.3-01M : Metadata standard(s) that are listed in re3data are excluded from the assessment output.'
                )



        elif self.fuji.use_datacite:
            self.logger.warning('FsF-R1.3-01M : NO metadata standard(s) of the repository specified in re3data')

        if community_standards_detected:
            if re3_detected:
                if self.maturity < 3:
                    self.maturity = 2
                    self.setEvaluationCriteriumScore('FsF-R1.3-01M-2', 1, 'pass')
                else:
                    self.setEvaluationCriteriumScore('FsF-R1.3-01M-2', 0, 'pass')
            if len(community_standards_detected) - len(multidiscipliary_standards_detected) > 0:
                self.score.earned = self.total_score
            self.result.test_status = 'pass'

        else:
            self.logger.warning('FsF-R1.3-01M : Unable to determine community standard(s)')
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.output = community_standards_detected
