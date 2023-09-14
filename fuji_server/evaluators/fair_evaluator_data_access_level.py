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
    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        #if self.fuji.metric_helper.get_metric_version() <= 0.5:
        self.set_metric('FsF-A1-01M')
        #else:
        #    self.set_metric('FsF-R1.1-02M')
        self.access_details = {}
        self.access_level = None
        #self.access_rights_dict = self.fuji.ACCESS_RIGHTS
        self.lower_case_access_dict = {k.get('id').lower():k.get('access_condition') for ak, av in self.fuji.ACCESS_RIGHTS.items() for k in av.get('members')}
        self.ACCESS_RIGHT_CODES = {k.get('id'):k.get('access_condition') for ak,av in self.fuji.ACCESS_RIGHTS.items() for k in av.get('members')}
        self.ACCESS_RIGHT_CODES.update({k.get('label').lower():k.get('access_condition') for ak,av in self.fuji.ACCESS_RIGHTS.items() for k in av.get('members')})
        #self.lower_case_access_dict = dict((k.lower(), v) for k, v in Mapper.ACCESS_RIGHT_CODES.value.items())
    def excludeLicences(self, access_rights):
        licence_evaluator = FAIREvaluatorLicense(self.fuji)
        real_access_rights = []
        if access_rights:
            for access_right in access_rights:
                if isinstance(access_right, str):
                    access_right = re.sub(r'[\r\n]+', ' ', access_right)
                    if not licence_evaluator.isLicense(
                            value=access_right,
                            metric_id=self.metric_identifier):  # exclude license-based text from access_rights
                        real_access_rights.append(access_right)
                        self.logger.info(
                            self.metric_identifier + ' : Access condition does not look like license, therefore continuing -: {}'.format(access_right))
                    else:
                        self.logger.warning(
                            self.metric_identifier + ' : Access condition looks like license, therefore the following is ignored -: {}'.
                                format(access_right))
                        if self.fuji.metadata_merged.get('license'):
                            if isinstance(self.fuji.metadata_merged.get('license'), list):
                                self.fuji.metadata_merged['license'].append(access_right)
                            else:
                                self.fuji.metadata_merged['license'] = [access_right]
                        self.logger.info(
                            'FsF-R1.1-01M : License expressed as access condition (rights), therefore moved from FsF-A1-01M -: {}'
                                .format(access_right))
        return real_access_rights

    def testAccessRightsMetadataAvailable(self, access_rights):
        test_result = False
        if self.isTestDefined(self.metric_identifier + '-1'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-1')
            if access_rights:
                test_result = True
                self.logger.info(self.metric_identifier +' : Found access rights information in dedicated metadata element -: '+str(access_rights))
                self.setEvaluationCriteriumScore(self.metric_identifier + '-1',test_score, 'pass')
                self.score.earned = test_score
                self.maturity = self.metric_tests.get(self.metric_identifier + '-1').metric_test_maturity_config
            else:
                self.logger.warning(self.metric_identifier +' : NO access information is available in metadata')
        return test_result

    def testAccessRightsStandardTerms(self,access_rights):
        test_result = False
        if self.isTestDefined(self.metric_identifier + '-3'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-3')
            if access_rights:
                for access_right in access_rights:
                    if access_right.lower() in self.lower_case_access_dict:
                        self.logger.info(
                            self.metric_identifier + ' : Non-actionable (term only) standard access level recognized as -:' +
                            str(self.lower_case_access_dict.get(access_right.lower())))
                        self.maturity = self.metric_tests.get(self.metric_identifier + '-3').metric_test_maturity_config
                        self.setEvaluationCriteriumScore(self.metric_identifier + '-3', test_score, 'pass')
                        self.access_level = self.lower_case_access_dict.get(access_right.lower())
                        self.access_details['access_condition'] = access_right
                        self.score.earned = test_score
                        break
            else:
                self.logger.info(self.metric_identifier +' : Skipping standard terms test since NO access information is available in metadata')

        return test_result

    def getIsAccessibleForFreeTerm(self):
        access_rights = []
        afree_uri = None
        #schema.org/accessiblefroFree
        access_free = self.fuji.metadata_merged.get('access_free')
        if access_free is not None:
            self.logger.info(
                self.metric_identifier + ' : Found \'schema.org/isAccessibleForFree\' to determine the access level (either public or restricted)'
            )
            if access_free:  # schema.org: isAccessibleForFree || free
                access_rights = 'public'
            else:
                access_rights = 'restricted'
            afree_uri = 'https://schema.org/isAccessibleForFree#' + str(access_rights)

        return access_rights,afree_uri

    def testAccessRightsMachineReadable(self,access_rights):
        test_result = False
        if self.isTestDefined(self.metric_identifier + '-2'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-2')
            #Hier stimmt was nicht!!!
            rights_regex = r'((info\:eu\-repo\/semantics|schema.org\/isAccessibleForFree|purl.org\/coar\/access_right|vocabularies\.coar-repositories\.org\/access_rights|purl\.org\/eprint\/accessRights|europa\.eu\/resource\/authority\/access-right)[\/#]{1}(\S*))'
            if not access_rights:
                access_free = self.fuji.metadata_merged.get('access_free')
            if access_rights:
                for access_right in access_rights:
                    self.logger.info(self.metric_identifier + ' : Access right information specified -: {}'.format(
                        access_right))
                    print(rights_regex, access_right)
                    rights_match = re.search(rights_regex, access_right, re.IGNORECASE)
                    if rights_match is not None:
                        print('########################################')
                        last_group = len(rights_match.groups())
                        filtered_rights = rights_match[last_group]
                        for right_code, right_status in self.ACCESS_RIGHT_CODES.items():
                            if re.search(right_code, filtered_rights, re.IGNORECASE):
                                test_result = True
                                self.access_level = right_status
                                self.access_details['access_condition'] = rights_match[1]  # overwrite existing condition
                                self.logger.info(self.metric_identifier + ' : Standardized actionable access level recognized as -:' +
                                                 str(right_status))
                                self.setEvaluationCriteriumScore(self.metric_identifier + '-2', test_score, 'pass')
                                self.score.earned = test_score
                                self.maturity = self.metric_tests.get(self.metric_identifier + '-2').metric_test_maturity_config
                                break
                        break
            else:
                self.logger.info(self.metric_identifier +' : Skipping machine readablility test since NO access information is available in metadata')
        return test_result

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

        test_status = 'fail'
        access_rights = self.fuji.metadata_merged.get('access_level')
        if isinstance(access_rights, str):
            access_rights = [access_rights]
        access_rights = self.excludeLicences(access_rights)
        #access_rights can be None or []
        if self.testAccessRightsMetadataAvailable(access_rights):
            test_status = 'pass'
        if self.testAccessRightsStandardTerms(access_rights):
            test_status = 'pass'
        else:
            try:
                afreeterm, afreeuri = self.getIsAccessibleForFreeTerm()
                if afreeuri:
                    access_rights.extend([afreeuri])
                    self.access_level = afreeterm
                if self.testAccessRightsStandardTerms(access_rights):
                    test_status = 'pass'
            except:
                pass

        if self.testAccessRightsMachineReadable(access_rights):
            test_status = 'pass'

        if not self.access_details and access_rights:
            if access_rights:
                self.access_details['access_condition'] = ', '.join(access_rights)

       #if embargoed, publication date must be specified (for now score is not deducted, just outputs warning message)
        if self.access_level == 'embargoed':
            available_date = self.fuji.metadata_merged.get('publication_date')
            if available_date:
                self.logger.info(self.metric_identifier + ' : Embargoed access, available date -: {}'.format(available_date))
                self.access_details['available_date'] = available_date
            else:
                self.logger.warning(self.metric_identifier + ' : Embargoed access, available date NOT found')

        if self.access_level or self.access_details:
            test_status = 'pass'
        self.result.score = self.score
        self.result.test_status = test_status

        if self.access_level:  #must be one of ['public', 'embargoed', 'restricted', 'closed','metadataonly']
            self.output.access_level = self.access_level
            self.logger.log(self.fuji.LOG_SUCCESS,
                            self.metric_identifier + ' : Access level to data could successfully be determined -: ' + self.access_level)
        else:
            self.logger.warning(self.metric_identifier + ' : Unable to determine the access level')
        self.output.access_details = self.access_details
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = self.output
