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
from fuji_server.models.data_provenance import DataProvenance
from fuji_server.models.data_provenance_output import DataProvenanceOutput
from fuji_server.models.data_provenance_output_inner import DataProvenanceOutputInner
from fuji_server.helper.metadata_mapper import Mapper


class FAIREvaluatorDataProvenance(FAIREvaluator):
    """
    A class to evaluate metadata that includes provenance information about data creation or generation (R1.2-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    -------
    evaluate()
        This method will evaluate the provenance information such as properties representing data creation,
        e.g., creator, contributor, modification date, version, source, and relations that indicate
        data creation activities. Moreover, it evaluates whether provenance information is available in
        a machine-readabe version such PROV-O or PAV
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric('FsF-R1.2-01M')


    def testProvenanceMetadataAvailable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-1'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-1')
            provenance_metadata_output = DataProvenanceOutputInner()
            provenance_metadata_output.provenance_metadata = []
            provenance_metadata_output.is_available = False
            self.logger.info(self.metric_identifier + ' : Check if provenance information is available in descriptive metadata')
            for md in self.fuji.metadata_merged:
                if md in Mapper.PROVENANCE_MAPPING.value:
                    provenance_metadata_output.is_available = True
                    provenance_metadata_output.provenance_metadata.append({
                        'prov_o_mapping':
                        Mapper.PROVENANCE_MAPPING.value.get(md),
                        'metadata_element':
                        md,
                        'metadata_value':
                        self.fuji.metadata_merged.get(md)
                    })

            relateds = self.fuji.metadata_merged.get('related_resources')
            self.logger.info(
                self.metric_identifier + ' : Check if provenance information is available in metadata about related resources')
            if isinstance(relateds, list):
                for rm in relateds:
                    if rm.get('relation_type') in Mapper.PROVENANCE_MAPPING.value:
                        provenance_metadata_output.provenance_metadata.append({
                            'prov_o_mapping':
                            Mapper.PROVENANCE_MAPPING.value.get(rm.get('relation_type')),
                            'metadata_element':
                            'related.' + str(rm.get('relation_type')),
                            'metadata_value':
                            rm.get('related_resource')
                        })
            else:
                self.logger.warning(self.metric_identifier + ' : No provenance information found in metadata about related resources')

            if provenance_metadata_output.is_available:
                test_status = True
                self.logger.log(self.fuji.LOG_SUCCESS, self.metric_identifier + ' : Found data creation-related provenance information')
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + '-1')
                self.score.earned = test_score
                self.setEvaluationCriteriumScore(self.metric_identifier + '-1', test_score, 'pass')
            self.output.provenance_metadata_included = provenance_metadata_output
        return test_status

    def testProvenanceStandardsUsed(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + '-2'):
            test_score = self.getTestConfigScore(self.metric_identifier + '-2')
            provenance_namespaces = ['http://www.w3.org/ns/prov#', 'http://purl.org/pav/']
            # structured provenance metadata available
            structured_metadata_output = DataProvenanceOutputInner()
            structured_metadata_output.provenance_metadata = []
            structured_metadata_output.is_available = False
            self.logger.info(self.metric_identifier + ' : Check if provenance specific namespaces are listed in metadata')

            used_provenance_namespace = list(set(provenance_namespaces).intersection(set(self.fuji.namespace_uri)))
            if used_provenance_namespace:
                test_status = True
                self.score.earned += test_score
                structured_metadata_output.is_available = True
                for used_prov_ns in used_provenance_namespace:
                    structured_metadata_output.provenance_metadata.append({'namespace': used_prov_ns})
                self.setEvaluationCriteriumScore(self.metric_identifier + '-2', test_score, 'pass')
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + '-2')
                self.logger.log(self.fuji.LOG_SUCCESS, self.metric_identifier + ' : Found use of dedicated provenance ontologies')
            else:
                self.logger.warning(self.metric_identifier + ' : Formal provenance metadata is unavailable')
            self.output.structured_provenance_available = structured_metadata_output
        return test_status

    def evaluate(self):
        self.result = DataProvenance(id=self.metric_number,
                                     metric_identifier=self.metric_identifier,
                                     metric_name=self.metric_name)
        self.output = DataProvenanceOutput()

        provenance_status = 'fail'
        if self.testProvenanceMetadataAvailable():
            provenance_status = 'pass'
        if self.testProvenanceStandardsUsed():
            provenance_status = 'pass'
            
        self.result.test_status = provenance_status
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = self.output
        self.result.score = self.score
