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

from urllib.parse import urlparse

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.models.standardised_protocol_metadata import StandardisedProtocolMetadata
from fuji_server.models.standardised_protocol_metadata_output import StandardisedProtocolMetadataOutput


class FAIREvaluatorStandardisedProtocolMetadata(FAIREvaluator):
    """
    A class to evaluate whether the metadata is accessible through a standardized communication protocol (A1-02M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate the accesibility of the metadata on whether the URI's scheme is based on
        a shared application protocol.

    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric("FsF-A1-02M")
        self.metadata_output = {}

    def testStandardProtocolMetadataUsed(self):
        test_status = False
        if self.isTestDefined(self.metric_identifier + "-1"):
            test_score = self.getTestConfigScore(self.metric_identifier + "-1")
            if self.fuji.landing_url is not None:
                metadata_required = Mapper.REQUIRED_CORE_METADATA.value
                metadata_found = {k: v for k, v in self.fuji.metadata_merged.items() if k in metadata_required}
                # parse the URL and return the protocol which has to be one of Internet RFC on
                # Relative Uniform Resource Locators
                metadata_parsed_url = urlparse(self.fuji.landing_url)
                metadata_url_scheme = metadata_parsed_url.scheme
                if len(self.fuji.metadata_merged) == 0:
                    self.logger.warning(
                        self.metric_identifier
                        + " : No metadata given or found, therefore the protocol of given PID was not assessed. See: FsF-F2-01M"
                    )
                else:
                    if metadata_url_scheme in self.fuji.STANDARD_PROTOCOLS:
                        self.logger.log(
                            self.fuji.LOG_SUCCESS,
                            "FsF-A1-02M : Standard protocol for access to metadata found -: "
                            + str(metadata_url_scheme),
                        )

                        self.metadata_output = {
                            metadata_url_scheme: self.fuji.STANDARD_PROTOCOLS.get(metadata_url_scheme)
                        }
                        test_status = True
                        self.score.earned = test_score
                        self.setEvaluationCriteriumScore(self.metric_identifier + "-1", test_score, "pass")
                        self.maturity = self.getTestConfigMaturity(self.metric_identifier + "-1")
                    # TODO: check why this is tested - delete if not required
                    if set(metadata_found) != set(metadata_required):
                        self.logger.info("FsF-A1-02M : NOT all required metadata given, see: FsF-F2-01M")
                        # parse the URL and return the protocol which has to be one of Internet RFC on Relative Uniform Resource Locators
            else:
                self.logger.warning("FsF-A1-02M : Metadata Identifier is not actionable or protocol errors occurred")
        return test_status

    def evaluate(self):
        self.result = StandardisedProtocolMetadata(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )
        test_status = "fail"

        if self.testStandardProtocolMetadataUsed():
            test_status = "pass"
        self.result.score = self.score
        self.result.output = StandardisedProtocolMetadataOutput(standard_metadata_protocol=self.metadata_output)
        self.result.metric_tests = self.metric_tests
        self.result.maturity = self.maturity
        self.result.test_status = test_status
