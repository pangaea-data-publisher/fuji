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
from fuji_server.models.semantic_vocabulary import SemanticVocabulary
from fuji_server.models.semantic_vocabulary_output_inner import SemanticVocabularyOutputInner
from fuji_server.helper.linked_vocab_helper import linked_vocab_helper


class FAIREvaluatorSemanticVocabulary(FAIREvaluator):
    """
    A class to evaluate whether the metadata uses semantic resources (I1-02M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate the metadata uses namespace of known semantic resources are present in
        the metadata of an object. These common namespaces such as RDF, RDFS, XSD, OWL, etc, will be
        excluded from the evaluation.
    """
    def evaluate(self):
        lov_helper = linked_vocab_helper(self.fuji.LINKED_VOCAB_INDEX)
        self.result = SemanticVocabulary(id=self.metric_number,
                                         metric_identifier=self.metric_identifier,
                                         metric_name=self.metric_name)

        # remove duplicates
        #print(self.fuji.namespace_uri)
        #print(self.fuji.linked_namespace_uri)
        if self.fuji.namespace_uri:
            self.fuji.namespace_uri = list(set(self.fuji.namespace_uri))
            self.fuji.namespace_uri = [x.strip().rstrip('/#') for x in self.fuji.namespace_uri]
        self.logger.info('{0} : Number of vocabulary namespaces extracted from all RDF-based metadata -: {1}'.format(
            self.metric_identifier, len(self.fuji.namespace_uri)))

        self.logger.info('{0} : Number of vocabulary namespaces extracted from all RDF-based metadata -: {1}'.format(
            self.metric_identifier, len(self.fuji.namespace_uri)))

        # exclude white list
        excluded = []
        for n in self.fuji.namespace_uri:
            for i in self.fuji.DEFAULT_NAMESPACES:
                if n.startswith(i):
                    #print(i, n)
                    excluded.append(n)
        self.fuji.namespace_uri[:] = [x for x in self.fuji.namespace_uri if x not in excluded]
        if excluded:
            self.logger.info('{0} : Default vocabulary namespace(s) excluded -: {1}'.format(
                self.metric_identifier, excluded))

        outputs = []
        score = 0
        test_status = 'fail'
        # test if exists in imported list, and the namespace is assumed to be active as it is tested during the LOD import.
        if self.fuji.namespace_uri or self.fuji.linked_namespace_uri:
            self.maturity = 1
            self.setEvaluationCriteriumScore('FsF-I2-01M-1', 0, 'pass')
        exists = []
        if self.fuji.namespace_uri:
            self.logger.info('{0} : Check if the remaining namespace(s) exist(s) in a LOD registry -: {1}'.format(
                self.metric_identifier, self.fuji.namespace_uri))
            lod_namespaces = [d['namespace'].strip().rstrip('/#') for d in self.fuji.VOCAB_NAMESPACES if 'namespace' in d]
            exists = list(set(lod_namespaces) & set(self.fuji.namespace_uri))
            for ns_uri in self.fuji.namespace_uri:
                lov_entry = lov_helper.get_linked_vocab_by_iri(ns_uri, isnamespaceIRI=True)
                if lov_entry and ns_uri not in exists:
                   exists.append(ns_uri)
        if self.fuji.linked_namespace_uri:
            self.logger.info('{0} : Check if known namespace(s) are used in linked property URIs which exist(s) in a LOD registry -: {1}'.format(
                self.metric_identifier, self.fuji.linked_namespace_uri.keys()))
            for linked_ns, linked_ns_data in self.fuji.linked_namespace_uri.items():
                linked_ns = linked_ns.strip().rstrip('/#')
                if linked_ns not in exists:
                    linked_exclude = False
                    for i in self.fuji.DEFAULT_NAMESPACES:
                        if linked_ns.startswith(i):
                            linked_exclude = True
                            break
                    if not linked_exclude:
                        #linked_lov_entry = lov_helper.get_linked_vocab_by_iri(linked_ns, isnamespaceIRI=True)
                        #if linked_lov_entry:
                        exists.append(linked_ns)
        if exists:
            score = self.total_score
            self.setEvaluationCriteriumScore('FsF-I2-01M-2', 1, 'pass')
            self.maturity = 3
            self.logger.log(self.fuji.LOG_SUCCESS,
                            '{0} : Namespace matches found -: {1}'.format(self.metric_identifier, exists))
            for e in exists:
                outputs.append(SemanticVocabularyOutputInner(namespace=e, is_namespace_active=True))
        else:
            self.logger.warning('{0} : NO vocabulary namespace match is found'.format(self.metric_identifier))

        not_exists = [x for x in self.fuji.namespace_uri if x not in exists]
        if not_exists:
            self.logger.warning(
                '{0} : Vocabulary namespace (s) or URIs specified but no match is found in LOD reference list (examples) -: {1}'.
                format(self.metric_identifier, not_exists[:10]))

        if not self.fuji.namespace_uri and not self.fuji.linked_namespace_uri:
            self.logger.warning('{0} : NO namespaces of semantic vocabularies found in the metadata'.format(
                self.metric_identifier))

        if score > 0:
            test_status = 'pass'

        self.result.test_status = test_status
        self.score.earned = score
        self.result.score = self.score
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = outputs
