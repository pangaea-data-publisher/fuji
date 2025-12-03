# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import fnmatch

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.linked_vocab_helper import LinkedVocabHelper
from fuji_server.models.semantic_vocabulary import SemanticVocabulary
from fuji_server.models.semantic_vocabulary_output_inner import SemanticVocabularyOutputInner


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

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-I2-01M")
        self.outputs = []
        self.knownnamespaceuris = []

    def setCommunityRequirements(self):
        test_requirements = []
        reqsdefined = False
        if self.metric_tests[self.metric_identifier + "-2"].metric_test_requirements:
            test_requirements = self.metric_tests[self.metric_identifier + "-2"].metric_test_requirements[0]
        if test_requirements:
            community_vocabs = []
            if test_requirements.get("required"):
                test_required = []
                if isinstance(test_requirements.get("required"), list):
                    test_required = test_requirements.get("required")
                elif test_requirements.get("required").get("identifier"):
                    test_required = test_requirements.get("required").get("identifier")
                if not isinstance(test_required, list):
                    test_required = [test_required]
                reqsdefined = True
                self.logger.info(
                    "{} : Will exclusively consider community specific vocabularies which are specified in metrics -: {}".format(
                        self.metric_identifier, test_requirements.get("required")
                    )
                )
                for rq_vocab in test_required:
                    for kn_vocab in self.knownnamespaceuris:
                        if fnmatch.fnmatch(kn_vocab, rq_vocab):
                            community_vocabs.append(kn_vocab)
                if len(community_vocabs) > 0:
                    self.logger.info(
                        "{} : Namespaces of community specific vocabularies found -: {}".format(
                            self.metric_identifier, community_vocabs
                        )
                    )
                self.knownnamespaceuris = [x for x in self.knownnamespaceuris if x in community_vocabs]
        return reqsdefined

    def testSemanticNamespaceURIsAvailable(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            if self.fuji.namespace_uri or self.fuji.linked_namespace_uri:
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + "-1")
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                self.score.earned += test_status
                test_status = True
                self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
            else:
                self.logger.warning(
                    f"{self.metric_identifier} : NO namespaces of semantic vocabularies found in the metadata"
                )
        return test_status

    def testKnownSemanticResourcesUsed(self):
        lov_helper = LinkedVocabHelper(self.fuji.LINKED_VOCAB_INDEX)
        test_status = False
        communityspecsdefined = False
        if self.isTestDefined(self.metric_identifier + "-2"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-2")
            if not self.fuji.namespace_uri and not self.fuji.linked_namespace_uri:
                self.logger.info(
                    "{} : Skipping namespace lookup in LOD registry list since no namespaces available".format(
                        self.metric_identifier
                    )
                )
            if self.fuji.namespace_uri:
                self.logger.info(
                    "{} : Check if known namespace(s) are used in structured metadata (RDF, XML) which exist(s) in a LOD registry -: {}".format(
                        self.metric_identifier, self.fuji.namespace_uri
                    )
                )
                for ns_uri in self.fuji.namespace_uri:
                    lov_entry = lov_helper.get_linked_vocab_by_iri(ns_uri, isnamespaceIRI=True)
                    if lov_entry and ns_uri not in self.knownnamespaceuris:
                        self.knownnamespaceuris.append(ns_uri)

            if self.fuji.linked_namespace_uri:
                self.logger.info(
                    "{} : Check if known namespace(s) are used in linked property URIs which exist(s) in a LOD registry -: {}".format(
                        self.metric_identifier, self.fuji.linked_namespace_uri
                    )
                )
                for ns_uri in self.fuji.linked_namespace_uri:
                    lov_entry = lov_helper.get_linked_vocab_by_iri(ns_uri, isnamespaceIRI=True)
                    if lov_entry and ns_uri not in self.knownnamespaceuris:
                        self.knownnamespaceuris.append(ns_uri)

            communityspecsdefined = self.setCommunityRequirements()
            if self.knownnamespaceuris:
                test_status = True
                self.score.earned += test_score
                self.maturity = self.getTestConfigMaturity(self.metric_identifier + "-2")
                self.setEvaluationCriteriumScore(self.metric_identifier + "-2", test_score, "pass")
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    f"{self.metric_identifier} : Namespace matches found -: {self.knownnamespaceuris}",
                )
                for e in self.knownnamespaceuris:
                    self.outputs.append(SemanticVocabularyOutputInner(namespace=e, is_namespace_active=True))
                not_exists = [x for x in self.fuji.namespace_uri if x not in self.knownnamespaceuris]
                if not_exists:
                    self.logger.warning(
                        "{} : Vocabulary namespace(s) or URIs specified but no match is found in LOD reference list (examples) -: {}".format(
                            self.metric_identifier, not_exists[:10]
                        )
                    )
            else:
                if communityspecsdefined:
                    self.logger.warning(
                        "{} : NO community specific vocabulary namespace URI is found which is listed in the LOD registry".format(
                            self.metric_identifier
                        )
                    )
                else:
                    self.logger.warning(
                        "{} : NO known vocabulary namespace URI is found which is listed in  the LOD registry".format(
                            self.metric_identifier
                        )
                    )

        return test_status

    def removeDefaultVocabularies(self, vocablist):
        vocablist = list(set(vocablist))
        vocablist = [x.strip().rstrip("/#") for x in vocablist]

        excluded = []
        for n in vocablist:
            for i in self.fuji.DEFAULT_NAMESPACES:
                if n.startswith(i):
                    excluded.append(n)
        vocablist[:] = [x for x in vocablist if x not in excluded]
        if excluded:
            self.logger.info(f"{self.metric_identifier} : Default vocabulary namespace(s) excluded -: {excluded}")
        return vocablist

    def evaluate(self):
        self.result = SemanticVocabulary(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )

        # outputs = []
        test_status = "fail"
        # remove duplicates and default namespaces
        if len(self.fuji.namespace_uri) > 0:
            self.logger.info(
                "{} : Removing default namespaces from {} vocabulary namespaces found in structured metadata".format(
                    self.metric_identifier, len(self.fuji.namespace_uri)
                )
            )
            self.fuji.namespace_uri = self.removeDefaultVocabularies(self.fuji.namespace_uri)
        if len(self.fuji.linked_namespace_uri) > 0:
            self.logger.info(
                "{} : Removing default namespaces from {} vocabulary namespaces extracted from links found in metadata".format(
                    self.metric_identifier, len(self.fuji.linked_namespace_uri)
                )
            )
            self.fuji.linked_namespace_uri = self.removeDefaultVocabularies(self.fuji.linked_namespace_uri)

        if self.testSemanticNamespaceURIsAvailable():
            test_status = "pass"
        if self.testKnownSemanticResourcesUsed():
            test_status = "pass"

        self.result.test_status = test_status
        self.result.score = self.score
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = self.outputs
