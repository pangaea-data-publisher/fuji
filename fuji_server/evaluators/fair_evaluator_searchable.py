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
from fuji_server import OutputSearchMechanisms
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.searchable import Searchable
from fuji_server.models.searchable_output import SearchableOutput
from fuji_server.helper.metadata_collector import MetaDataCollector
from typing import List, Any

class FAIREvaluatorSearchable(FAIREvaluator):
    def evaluate(self):
        self.result = Searchable(id=self.fuji.count, metric_identifier=self.metric_identifier, metric_name=self.metric_name)
        self.output = SearchableOutput()

        search_mechanisms = []
        sources_registry = [MetaDataCollector.Sources.DATACITE_JSON.value]
        all = str([e.value for e in MetaDataCollector.Sources]).strip('[]')
        self.logger.info('FsF-F4-01M : Supported tests of metadata retrieval/extraction - {}'.format(all))
        search_engines_support = [MetaDataCollector.Sources.SCHEMAORG_NEGOTIATE.value,
                                  MetaDataCollector.Sources.SCHEMAORG_EMBED.value,
                                  MetaDataCollector.Sources.DUBLINCORE.value,
                                  MetaDataCollector.Sources.RDFA.value]
        # Check search mechanisms based on sources of metadata extracted.
        search_engine_support_match: List[Any] = list(set(dict(self.fuji.metadata_sources).keys()).intersection(search_engines_support))
        if search_engine_support_match:
            self.setEvaluationCriteriumScore('FsF-F4-01M-1', 1, 'pass')
            search_mechanisms.append(
                OutputSearchMechanisms(mechanism='structured data', mechanism_info=search_engine_support_match))
            self.logger.info('FsF-F4-01M : Metadata found through - structured data')
        else:
            self.logger.warning('FsF-F4-01M : Metadata is NOT found through - {}'.format(search_engines_support))
        #TODO: replace this metadata format based test by real lookup at registries
        registry_support_match = list(set(dict(self.fuji.metadata_sources).keys()).intersection(sources_registry))
        if registry_support_match:
            self.setEvaluationCriteriumScore('FsF-F4-01M-2', 1, 'pass')
            search_mechanisms.append(
                OutputSearchMechanisms(mechanism='metadata registry', mechanism_info=registry_support_match))
            self.logger.info('FsF-F4-01M : Metadata found through - metadata registry')
        else:
            self.logger.warning(
                'FsF-F4-01M : Metadata is NOT found through registries considered by the assessment service  - {}'.format(
                    sources_registry))
        length = len(search_mechanisms)
        if length > 0:
            self.result.test_status = 'pass'

            if length == 2:
                self.score.earned = self.total_score
            if length == 1:
                self.score.earned = self.total_score - 1
        else:
            self.logger.warning('NO search mechanism supported')

        self.result.score =  self.score
        self.output.search_mechanisms = search_mechanisms
        self.result.metric_tests = self.metric_tests
        self.result.output =  self.output
