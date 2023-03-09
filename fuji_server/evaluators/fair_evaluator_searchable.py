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
from fuji_server.helper.catalogue_helper_datacite import MetaDataCatalogueDataCite
from fuji_server.helper.catalogue_helper_google_datasearch import MetaDataCatalogueGoogleDataSearch
from fuji_server.helper.catalogue_helper_mendeley_data import MetaDataCatalogueMendeleyData
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.models.searchable import Searchable
from fuji_server.models.searchable_output import SearchableOutput
from fuji_server.helper.metadata_collector import MetaDataCollector
from fuji_server.helper.catalogue_helper import MetaDataCatalogue
from typing import List, Any


class FAIREvaluatorSearchable(FAIREvaluator):
    """
    A class to evaluate whether the metadata is offered to be retrievable by the machine (F4-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the metadata is registered in major research data registries such as DataCite or
        the metadata is given in a way major search engines can ingest it, e.g., JSON-LD, Dublin Core, RDFa.
    """

    def check_registry_support(self):
        # check if record is listed in major catalogs -> searchable
        # DataCite registry, Google Dataset search, Mendeley data etc..
        #Using the DataCite API in case content negotiation does not work
        registries_supported = []
        if self.fuji.pid_url or self.fuji.landing_url:
            #DataCite only for DOIs
            pidhelper = IdentifierHelper(self.fuji.pid_url)
            if self.fuji.pid_scheme:
                if 'doi' in self.fuji.pid_scheme:
                    datacite_registry_helper = MetaDataCatalogueDataCite(self.fuji.logger)
                    datacite_registry_helper.query(pidhelper.normalized_id)
                    if datacite_registry_helper.islisted:
                        registries_supported.append(datacite_registry_helper.source)
            if not registries_supported:
                google_registry_helper = MetaDataCatalogueGoogleDataSearch(self.fuji.logger, self.fuji.metadata_merged.get('object_type'))
                google_registry_helper.query([pidhelper.normalized_id, self.fuji.landing_url])
                if google_registry_helper.islisted:
                    registries_supported.append(google_registry_helper.source)
            else:
                self.logger.info(
                    'FsF-F4-01M : Dataset already found in registry therefore skipping Google Dataset Search Cache query'
                )

            if not registries_supported:
                mendeley_registry_helper = MetaDataCatalogueMendeleyData(self.fuji.logger)
                mendeley_registry_helper.query([pidhelper.normalized_id, self.fuji.landing_url])
                if mendeley_registry_helper.islisted:
                    registries_supported.append(mendeley_registry_helper.source)
            else:
                self.logger.info(
                    'FsF-F4-01M : Dataset already found in registry therefore skipping Mendeley Data query')
        else:
            self.logger.warning(
                'FsF-F4-01M : No resolvable PID or responding landing page found, therefore skipping data catalogue coverage tests'
            )
        return registries_supported

    def evaluate(self):
        self.result = Searchable(id=self.metric_number,
                                 metric_identifier=self.metric_identifier,
                                 metric_name=self.metric_name)
        self.output = SearchableOutput()

        search_mechanisms = []
        sources_registry = [
            MetaDataCollector.Sources.DATACITE_JSON_NEGOTIATED.value, MetaDataCatalogue.Sources.DATACITE.value,
            MetaDataCatalogue.Sources.MENDELEY_DATA, MetaDataCatalogue.Sources.GOOGLE_DATASET
        ]
        all = str([e.value for e in MetaDataCollector.Sources]).strip('[]')
        self.logger.info('FsF-F4-01M : Supported tests of metadata retrieval/extraction -: {}'.format(all))
        search_engines_support = [
            MetaDataCollector.Sources.SCHEMAORG_NEGOTIATED.value, MetaDataCollector.Sources.SCHEMAORG_EMBEDDED.value,
            MetaDataCollector.Sources.DUBLINCORE_EMBEDDED.value, MetaDataCollector.Sources.RDFA_EMBEDDED.value
        ]
        # Check search mechanisms based on sources of metadata extracted.
        search_engine_support_match: List[Any] = list(
            set(dict(self.fuji.metadata_sources).keys()).intersection(search_engines_support))
        if search_engine_support_match:
            self.setEvaluationCriteriumScore('FsF-F4-01M-1', 1, 'pass')
            self.maturity = 3
            search_mechanisms.append(
                OutputSearchMechanisms(mechanism='structured data', mechanism_info=search_engine_support_match))
            self.logger.info('FsF-F4-01M : Metadata found through - structured data')
        else:
            self.logger.warning('FsF-F4-01M : Metadata is NOT found through -: {}'.format(search_engines_support))

        registries_listed = self.check_registry_support()
        registry_support_match = registries_listed
        if registry_support_match:
            self.setEvaluationCriteriumScore('FsF-F4-01M-2', 1, 'pass')
            if self.maturity < 3:
                self.maturity = 2
            search_mechanisms.append(
                OutputSearchMechanisms(mechanism='metadata registry', mechanism_info=registry_support_match))
            self.logger.info('FsF-F4-01M : Metadata found through - metadata registry')
        else:
            self.logger.warning(
                'FsF-F4-01M : Metadata is NOT found through registries considered by the assessment service  -: {}'.
                format(sources_registry))
        length = len(search_mechanisms)
        if length > 0:
            self.result.test_status = 'pass'
            if length == 2:
                self.score.earned = self.total_score
            if length == 1:
                self.score.earned = self.total_score - 1
        else:
            self.logger.warning('NO search mechanism supported')

        self.result.score = self.score
        self.output.search_mechanisms = search_mechanisms
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.output = self.output
