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
    def evaluate(self):

        self.result = DataProvenance(id=self.metric_number, metric_identifier=self.metric_identifier,
                                                metric_name=self.metric_name)
        self.output = DataProvenanceOutput()
        score = 0
        has_creation_provenance = False
        provenance_elements = []
        provenance_namespaces = ['http://www.w3.org/ns/prov#', 'http://purl.org/pav/']
        provenance_status = 'fail'

        provenance_metadata_output = DataProvenanceOutputInner()
        provenance_metadata_output.provenance_metadata = []
        provenance_metadata_output.is_available = False
        self.logger.info(
            'FsF-R1.2-01M : Check if provenance information is available in descriptive metadata')
        for md in self.fuji.metadata_merged:
            if md in Mapper.PROVENANCE_MAPPING.value:
                provenance_metadata_output.is_available = True
                provenance_metadata_output.provenance_metadata.append(
                    {'prov_o_mapping': Mapper.PROVENANCE_MAPPING.value.get(md), 'metadata_element': md,
                     'metadata_value': self.fuji.metadata_merged.get(md)}
                )

        relateds = self.fuji.metadata_merged.get('related_resources')
        self.logger.info(
            'FsF-R1.2-01M : Check if provenance information is available in metadata about related resources')
        if isinstance(relateds, list):
            for rm in relateds:
                if rm.get('relation_type') in Mapper.PROVENANCE_MAPPING.value:
                    provenance_metadata_output.provenance_metadata.append(
                        {'prov_o_mapping': Mapper.PROVENANCE_MAPPING.value.get(rm.get('relation_type')),
                         'metadata_element': 'related.' + str(rm.get('relation_type')),
                         'metadata_value': rm.get('related_resource')}
                    )
        else:
            self.logger.info('FsF-R1.2-01M : No provenance information found in metadata about related resources')


        if provenance_metadata_output.is_available:
            self.logger.log(self.fuji.LOG_SUCCESS,'FsF-R1.2-01M : Found data creation-related provenance information')
            provenance_status = 'pass'
            score = score + 1
            self.setEvaluationCriteriumScore('FsF-R1.2-01M-1', 1, 'pass')
        self.output.provenance_metadata_included = provenance_metadata_output

        # structured provenance metadata available
        structured_metadata_output = DataProvenanceOutputInner()
        structured_metadata_output.provenance_metadata = []
        structured_metadata_output.is_available = False
        self.logger.info(
            'FsF-R1.2-01M : Check if provenance specific namespaces are listed in metadata')

        used_provenance_namespace = list(set(provenance_namespaces).intersection(set(self.fuji.namespace_uri)))
        if used_provenance_namespace:
            score = score + 1
            structured_metadata_output.is_available = True
            for used_prov_ns in used_provenance_namespace:
                structured_metadata_output.provenance_metadata.append({'namespace': used_prov_ns})
            self.setEvaluationCriteriumScore('FsF-R1.2-01M-2', 1, 'pass')
            self.logger.log(self.fuji.LOG_SUCCESS, 'FsF-R1.2-01M : Found use of dedicated provenance ontologies')
        else:
            self.logger.warning('FsF-R1.2-01M : Formal provenance metadata is unavailable')
        self.output.structured_provenance_available = structured_metadata_output

        if score >= 1:
            provenance_status = 'pass'
        self.result.test_status = provenance_status
        self.score.earned = score
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output
        self.result.score = self.score