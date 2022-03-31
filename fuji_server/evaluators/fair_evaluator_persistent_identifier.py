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
from tldextract import extract

from fuji_server import Persistence, PersistenceOutput
from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.helper.identifier_helper import IdentifierHelper
from fuji_server.helper.metadata_mapper import Mapper
from fuji_server.helper.request_helper import RequestHelper, AcceptTypes
from urllib.parse import urlparse
import re
from bs4 import BeautifulSoup

class FAIREvaluatorPersistentIdentifier(FAIREvaluator):
    """
    A class to evaluate that the data is assigned a persistent identifier (F1-02D). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate whether the data is specified based on a commonly accepted persistent identifier scheme or
        the identifier is web-accesible, i.e., it resolves to a landing page with metadata of the data object.
    """

    def evaluate(self):
        self.result = Persistence(id=self.metric_number,
                                  metric_identifier=self.metric_identifier,
                                  metric_name=self.metric_name)
        self.output = PersistenceOutput()
        # ======= CHECK IDENTIFIER PERSISTENCE =======
        self.logger.info('FsF-F1-02D : PID schemes-based assessment supported by the assessment service - {}'.format(
            Mapper.VALID_PIDS.value))
        check_url = None
        signposting_pid = None
        if self.fuji.id_scheme is not None:
            check_url = self.fuji.pid_url
            #check_url = idutils.to_url(self.fuji.id, scheme=self.fuji.id_scheme)
        if self.fuji.id_scheme == 'url':
            self.fuji.origin_url = self.fuji.id
            check_url = self.fuji.id
        if check_url:
            # ======= RETRIEVE METADATA FROM LANDING PAGE =======
            requestHelper = RequestHelper(check_url, self.logger)
            requestHelper.setAcceptType(AcceptTypes.html_xml)  # request
            neg_source, self.fuji.extruct_result = requestHelper.content_negotiate('FsF-F1-02D', ignore_html=False)
            if not 'html' in str(requestHelper.content_type):
                self.logger.info('FsF-F2-01M :Content type is ' + str(requestHelper.content_type) +
                                 ', therefore skipping embedded metadata (microdata, RDFa) tests')
                self.fuji.extruct_result = {}
            if type(self.fuji.extruct_result) != dict:
                self.fuji.extruct_result = {}
            #r = requestHelper.getHTTPResponse()
            response_status = requestHelper.response_status

            if requestHelper.response_content:

                self.fuji.landing_url = requestHelper.redirect_url
                #in case the test has been repeated because a PID has been found in metadata
                #print(self.fuji.landing_url, self.fuji.input_id)
                if self.fuji.repeat_pid_check == True:
                    input_id_parts = extract(self.fuji.input_id)
                    landing_url_parts = extract(self.fuji.landing_url)
                    input_id_domain = input_id_parts.domain + '.' + input_id_parts.suffix
                    landing_domain = landing_url_parts.domain + '.' + landing_url_parts.suffix
                    if landing_domain != input_id_domain:
                        self.logger.warning(
                            'FsF-F1-02D : Landing page domain resolved from PID found in metadata does not match with input URL domain'
                        )
                        self.logger.warning(
                            'FsF-F2-01M : Seems to be a catalogue entry or alternative representation of the data set, landing page URL domain resolved from PID found in metadata does not match with input URL domain'
                        )

                        #self.fuji.repeat_pid_check = False
                if self.fuji.landing_url not in ['https://datacite.org/invalid.html']:

                    if response_status == 200:
                        # check if javascript generated content only:
                        try:
                            soup = BeautifulSoup(requestHelper.response_content, features="html.parser")
                            script_content = soup.findAll('script')
                            for script in soup(["script", "style", "title", "noscript"]):
                                script.extract()

                            text_content = soup.get_text(strip=True)
                            if (len(str(script_content)) > len(str(text_content))) and len(text_content) <= 150:
                                self.logger.warning('FsF-F1-02D : Landing page seems to be JavaScript generated, could not detect enough content')
                        except Exception as e:
                            pass
                        # identify signposting links in header
                        header_link_string = requestHelper.getResponseHeader().get('Link')
                        #header_link_string = requestHelper.getHTTPResponse().getheader('Link')
                        if header_link_string is not None:
                            for preparsed_link in header_link_string.split(','):
                                found_link = None
                                found_type, type_match = None, None
                                found_rel, rel_match = None, None
                                found_formats, formats_match = None, None
                                parsed_link = preparsed_link.strip().split(';')
                                found_link = parsed_link[0].strip()
                                for link_prop in parsed_link[1:]:
                                    link_prop=str(link_prop).strip()
                                    if link_prop.startswith('rel'):
                                        rel_match = re.search('rel\s*=\s*\"?([^,;"]+)\"?', link_prop)
                                    elif link_prop.startswith('type'):
                                        type_match = re.search('type\s*=\s*\"?([^,;"]+)\"?', link_prop)
                                    elif link_prop.startswith('formats'):
                                        formats_match = re.search('formats\s*=\s*\"?([^,;"]+)\"?', link_prop)
                                if type_match:
                                    found_type = type_match[1]
                                if rel_match:
                                    found_rel = rel_match[1]
                                if formats_match:
                                    found_formats = formats_match[1]
                                signposting_link_dict = {
                                    'url': found_link[1:-1],
                                    'type': found_type,
                                    'rel': found_rel,
                                    'profile': found_formats
                                }
                                if signposting_link_dict.get('url'):
                                    self.fuji.signposting_header_links.append(signposting_link_dict)

                            self.logger.info('FsF-F1-02D : Found signposting links in response header of landingpage -: ' + str(self.fuji.signposting_header_links))

                        #check if there is a cite-as signposting link
                        if self.fuji.pid_scheme is None:
                            signposting_pid_link = self.fuji.get_signposting_links('cite-as')
                            if signposting_pid_link:
                                signposting_pid = signposting_pid_link[0].get('url')
                            if signposting_pid:
                                signidhelper = IdentifierHelper
                                #found_ids = idutils.detect_identifier_schemes(signposting_pid[0])
                                found_id = signidhelper.preferred_schema
                                #if len(found_ids) > 1:
                                #    found_ids.remove('url')
                                #    found_id = found_ids[0]
                                if signidhelper.is_persistent:
                                    self.logger.info('FsF-F1-02D : Found object identifier in signposting header links')
                                    self.fuji.pid_scheme = found_id

                        up = urlparse(self.fuji.landing_url)
                        self.fuji.landing_origin = '{uri.scheme}://{uri.netloc}'.format(uri=up)
                        self.fuji.landing_html = requestHelper.getResponseContent()
                        self.fuji.landing_content_type = requestHelper.content_type

                        self.output.resolved_url = self.fuji.landing_url  # url is active, although the identifier is not based on a pid scheme
                        self.output.resolvable_status = True
                        self.logger.info('FsF-F1-02D : Object identifier active (status code = 200)')
                        self.fuji.isMetadataAccessible = True
                    elif response_status in [401, 402, 403]:
                        self.fuji.isMetadataAccessible = False
                        self.logger.warning(
                            'FsF-F1-02D : Resource inaccessible, identifier returned http status code -: {code}'.format(
                                code=response_status))
                    else:
                        self.fuji.isMetadataAccessible = False
                        self.logger.warning(
                            'FsF-F1-02D : Resource inaccessible, identifier returned http status code -: {code}'.format(
                                code=response_status))
                else:
                    self.logger.warning(
                        'FsF-F1-02D : Invalid DOI, identifier resolved to -: {code}'.format(code=self.fuji.landing_url))

            else:
                self.fuji.isMetadataAccessible = False
                self.logger.warning(
                    'FsF-F1-02D :Resource inaccessible, no response received from -: {}'.format(check_url))
                if response_status in [401, 402, 403]:
                    self.logger.warning(
                        'FsF-F1-02D : Resource inaccessible, identifier returned http status code -: {code}'.format(
                            code=response_status))
        else:
            self.logger.warning(
                'FsF-F1-02D :Resource inaccessible, could not identify an actionable representation for the given identfier -: {}'
                .format(self.fuji.id))

        if self.fuji.pid_scheme is not None:
            # short_pid = id.normalize_pid(self.id, scheme=pid_scheme)
            if signposting_pid is None:
                idhelper = IdentifierHelper(self.fuji.id)
                self.fuji.pid_url = idhelper.identifier_url
                #self.fuji.pid_url = idutils.to_url(self.fuji.id, scheme=self.fuji.pid_scheme)
            else:
                self.fuji.pid_url = signposting_pid[0]
            self.output.pid_scheme = self.fuji.pid_scheme

            self.output.pid = self.fuji.pid_url
            self.setEvaluationCriteriumScore('FsF-F1-02D-1', 0.5, 'pass')
            self.score.earned = 0.5
            self.maturity = 1
            if self.fuji.isMetadataAccessible:
                self.setEvaluationCriteriumScore('FsF-F1-02D-2', 0.5, 'pass')
                self.maturity = 3
                self.result.test_status = 'pass'
                self.score.earned = self.total_score  # idenfier should be based on a persistence scheme and resolvable

            #print(self.metric_tests)

            self.logger.log(self.fuji.LOG_SUCCESS,
                            'FsF-F1-02D : Persistence identifier scheme -: {}'.format(self.fuji.pid_scheme))
            #self.logger.info('FsF-F1-02D : Persistence identifier scheme - {}'.format(self.fuji.pid_scheme))
        else:
            self.score.earned = 0
            self.logger.warning('FsF-F1-02D : Not a persistent identifier scheme -: {}'.format(self.fuji.id_scheme))

        self.result.score = self.score
        self.result.maturity = self.maturity
        self.result.metric_tests = self.metric_tests
        self.result.output = self.output
