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

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.evaluators.fair_evaluator_license import FAIREvaluatorLicense
from fuji_server.models.data_access_level import DataAccessLevel
from fuji_server.models.data_access_output import DataAccessOutput
from fuji_server.helper.metadata_mapper import Mapper
import re


class FAIREvaluatorDataAccessLevel(FAIREvaluator):
    """
    A class to evaluate whether the metadata contains access level and access conditions of the data (A1-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate the metadata that includes the level of data access, e.g., public, embargoed, restricted, whether
        using a appropriate metadata field or using a machine-readable and verified against controlled vocabularies.
    """
    def evaluate(self):
        #Focus on machine readable rights -> URIs only
        #1) http://vocabularies.coar-repositories.org/documentation/access_rights/
        #2) Eprints AccessRights Vocabulary: check for http://purl.org/eprint/accessRights/
        #3) EU publications access rights check for http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC
        #4) Openaire Guidelines <dc:rights>info:eu-repo/semantics/openAccess</dc:rights>
        self.result = DataAccessLevel(self.metric_number,
                                      metric_identifier=self.metric_identifier,
                                      metric_name=self.metric_name)
        self.output = DataAccessOutput()
        licence_evaluator = FAIREvaluatorLicense(self.fuji)
        #rights_regex = r'((\/licenses|purl.org\/coar\/access_right|purl\.org\/eprint\/accessRights|europa\.eu\/resource\/authority\/access-right)\/{1}(\S*))'
        rights_regex = r'((\/creativecommons\.org|info\:eu\-repo\/semantics|purl.org\/coar\/access_right|purl\.org\/eprint\/accessRights|europa\.eu\/resource\/authority\/access-right)\/{1}(\S*))'

        access_level = None
        access_details = {}
        score = 0
        test_status = 'fail'
        exclude = []
        access_rights = self.fuji.metadata_merged.get('access_level')

        #access_rights can be None or []
        if access_rights:
            #self.logger.info('FsF-A1-01M : Found access rights information in dedicated metadata element')
            #self.setEvaluationCriteriumScore('FsF-A1-01M-1', 0.5, 'pass')
            #self.maturity = 1
            if isinstance(access_rights, str):
                access_rights = [access_rights]
            for access_right in access_rights:
                #TODO: remove new lines also from other logger messages or handle this elsewhere
                access_right = re.sub(r'[\r\n]+', ' ', access_right)
                self.logger.info('FsF-A1-01M : Access information specified -: {}'.format(
                    access_right.replace('\n', ' ')))
                if not licence_evaluator.isLicense(
                        value=access_right,
                        metric_id=self.metric_identifier):  # exclude license-based text from access_rights
                    rights_match = re.search(rights_regex, access_right, re.IGNORECASE)
                    if rights_match is not None:
                        last_group = len(rights_match.groups())
                        filtered_rights = rights_match[last_group]
                        for right_code, right_status in Mapper.ACCESS_RIGHT_CODES.value.items():
                            if re.search(right_code, filtered_rights, re.IGNORECASE):
                                access_level = right_status
                                access_details['access_condition'] = rights_match[1]  #overwrite existing condition
                                self.logger.info('FsF-A1-01M : Standardized actionable access level recognized as -:' +
                                                 str(right_status))
                                self.setEvaluationCriteriumScore('FsF-A1-01M-2', 0.5, 'pass')
                                self.maturity = 3
                                break
                        break
                    #else:
                    #    self.logger.info('FsF-A1-01M : Non-actionable, non-standardized, access level found')
                else:
                    self.logger.warning(
                        'FsF-A1-01M : Access condition looks like license, therefore the following is ignored -: {}'.
                        format(access_right))
                    if self.fuji.metadata_merged.get('license'):
                        if isinstance(self.fuji.metadata_merged.get('license'), list):
                            self.fuji.metadata_merged['license'].append(access_right)
                    else:
                        self.fuji.metadata_merged['license'] = [access_right]
                    self.logger.info(
                        'FsF-R1.1-01M : License expressed as access condition (rights), therefore moved from FsF-A1-01M -: {}'
                        .format(access_right))
                    exclude.append(access_right)

            if not access_level:
                lower_case_access_dict = dict((k.lower(), v) for k, v in Mapper.ACCESS_RIGHT_CODES.value.items())
                for access_right in access_rights:
                    if access_right.lower() in lower_case_access_dict:
                        self.logger.info(
                            'FsF-A1-01M : Non-actionable (term only) standard access level recognized as -:' +
                            str(lower_case_access_dict.get(access_right.lower())))
                        if self.maturity <= 2:
                            self.maturity = 2
                        self.setEvaluationCriteriumScore('FsF-A1-01M-3', 0.5, 'pass')
                        access_level = lower_case_access_dict.get(access_right.lower())
                        access_details['access_condition'] = access_right
                        break

            if not access_details and access_rights:
                access_rights = set(access_rights) - set(exclude)
                if access_rights:
                    access_details['access_condition'] = ', '.join(access_rights)

        if access_rights:
            self.logger.info('FsF-A1-01M : Found access rights information in dedicated metadata element')
            self.setEvaluationCriteriumScore('FsF-A1-01M-1', 0.5, 'pass')
            if self.maturity <= 1:
                self.maturity = 1
        else:
            self.logger.warning('FsF-A1-01M : NO access information is available in metadata')
            score = 0

        if access_level is None:
            # fall back - use binary access
            access_free = self.fuji.metadata_merged.get('access_free')
            if access_free is not None:
                self.logger.info(
                    'FsF-A1-01M : Used \'schema.org/isAccessibleForFree\' to determine the access level (either public or restricted)'
                )
                if access_free:  # schema.org: isAccessibleForFree || free
                    access_level = 'public'
                else:
                    access_level = 'restricted'
                access_details['accessible_free'] = access_free
                if self.maturity <= 2:
                    self.maturity = 2
                self.setEvaluationCriteriumScore('FsF-A1-01M-3', 0.5, 'pass')
            #TODO assume access_level = restricted if access_rights provided?

        #if embargoed, publication date must be specified (for now score is not deducted, just outputs warning message)
        if access_level == 'embargoed':
            available_date = self.fuji.metadata_merged.get('publication_date')
            if available_date:
                self.logger.info('FsF-A1-01M : Embargoed access, available date -: {}'.format(available_date))
                access_details['available_date'] = available_date
            else:
                self.logger.warning('FsF-A1-01M : Embargoed access, available date NOT found')

        if access_level or access_details:
            if access_level:
                score = 1
            else:
                score = 0.5
            test_status = 'pass'

        self.score.earned = score
        self.result.score = self.score
        self.result.test_status = test_status

        if access_level:  #must be one of ['public', 'embargoed', 'restricted', 'closed','metadataonly']
            self.output.access_level = access_level
            self.logger.log(self.fuji.LOG_SUCCESS,
                            'FsF-A1-01M : Access level to data could successfully be determined -: ' + access_level)
        else:
            self.logger.warning('FsF-A1-01M : Unable to determine the access level')
        self.output.access_details = access_details
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = self.output
