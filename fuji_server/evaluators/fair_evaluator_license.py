# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import fnmatch
import re

import idutils
import Levenshtein

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.license import License
from fuji_server.models.license_output_inner import LicenseOutputInner


class FAIREvaluatorLicense(FAIREvaluator):
    """
    A class to evaluate the license information under which data can be reused (R1.1-01M).
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate metadata information about license that is represented by
        using an appropriate metadata element and machine readable license

    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FsF-R1.1-01M", "FRSM-16-R1.1"])

        self.output = []
        self.license_info = []

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testLicenseIsValidAndSPDXRegistered": ["FsF-R1.1-01M-2", "FRSM-16-R1.1-2"],
            "testLicenseMetadataElementAvailable": ["FsF-R1.1-01M-1", "FRSM-16-R1.1-1"],
            "testLicenseMetadataZenodo": ["FRSM-16-R1.1-CESSDA-1"],
        }

    def setLicenseDataAndOutput(self):
        self.license_info = []
        specified_licenses = self.fuji.metadata_merged.get("license")
        if specified_licenses is None and self.metric_identifier.startswith("FRSM"):  # try GitHub data
            specified_licenses = self.fuji.github_data.get("license")
        if isinstance(specified_licenses, str):  # licenses maybe string or list depending on metadata schemas
            specified_licenses = [specified_licenses]
        if specified_licenses is not None and specified_licenses != []:
            for license in specified_licenses:
                isurl = False
                licence_valid = False
                license_output = LicenseOutputInner()
                if isinstance(license, str):
                    isurl = idutils.is_url(license)
                    if isurl:
                        iscc, generic_cc = self.isCreativeCommonsLicense(license, self.metric_identifier)
                        if iscc:
                            license = generic_cc
                        spdx_uri, spdx_osi, spdx_id = self.lookup_license_by_url(license, self.metric_identifier)
                    else:  # maybe licence name
                        spdx_uri, spdx_osi, spdx_id = self.lookup_license_by_name(license, self.metric_identifier)
                    license_output.license = license
                    if spdx_uri:
                        licence_valid = True
                    license_output.details_url = spdx_uri
                    license_output.osi_approved = spdx_osi
                    self.output.append(license_output)
                    self.license_info.append(
                        {
                            "license": license,
                            "id": spdx_id,
                            "is_url": isurl,
                            "spdx_uri": spdx_uri,
                            "osi_approved": spdx_osi,
                            "valid": licence_valid,
                        }
                    )
                    if not spdx_uri:
                        self.logger.warning(
                            f"{self.metric_identifier} : NO SPDX license representation (spdx url, osi_approved) found"
                        )
                    else:
                        self.logger.log(
                            self.fuji.LOG_SUCCESS,
                            f"{self.metric_identifier} : Found SPDX license representation (spdx url, osi_approved)",
                        )

    def isCreativeCommonsLicense(self, license_url, metric_id):
        iscc = False
        genericcc = None
        try:
            if "creativecommons.org/publicdomain/" in license_url:
                iscc = True
                self.logger.info(f"{metric_id} : Found CreativeCommons Public Domain Mark or License -: {license_url}")
                genericcc = "CC0-1.0"
            else:
                # https://wiki.creativecommons.org/wiki/License_Properties
                ccregex = r"https?://creativecommons\.org/licenses/(by(-nc)?(-nd)?(-sa)?)/(1\.0|2\.0|2\.5|3\.0|4\.0)"
                ccmatch = re.match(ccregex, license_url)
                if ccmatch:
                    self.logger.info(f"{metric_id} : Found CreativeCommons license -: {license_url}")
                    genericcc = ccmatch[0]
                    iscc = True
                else:
                    iscc = False
        except Exception:
            iscc = False
        return iscc, genericcc

    def isLicense(self, value, metric_id):
        islicense = False
        isurl = idutils.is_url(value)
        spdx_html = None
        spdx_osi = None
        if isurl:
            iscc, generic_cc = self.isCreativeCommonsLicense(value, metric_id)
            if iscc:
                islicense = True
            else:
                spdx_html, spdx_osi, spdx_id = self.lookup_license_by_url(value, metric_id)
        else:
            spdx_html, spdx_osi, spdx_id = self.lookup_license_by_name(value, metric_id)
        if spdx_html or spdx_osi:
            islicense = True
        return islicense

    def lookup_license_by_url(self, u, metric_id):
        self.logger.info(f"{metric_id} : Verify URL through SPDX registry -: {u}")
        html_url = None
        isOsiApproved = False
        id = None
        ul = None
        if "spdx.org/licenses" in u:
            ul = u.split("/")[-1]
        for item in self.fuji.SPDX_LICENSES:
            # u = u.lower()
            # if any(u in v.lower() for v in item.values()):
            licenseId = item.get("licenseId")
            seeAlso = item.get("seeAlso")
            if any(u in v for v in seeAlso) or licenseId == ul:
                self.logger.info("{} : Found SPDX license representation -: {}".format(metric_id, item["detailsUrl"]))
                # html_url = '.html'.join(item['detailsUrl'].rsplit('.json', 1))
                html_url = item["detailsUrl"].replace(".json", ".html")
                isOsiApproved = item["isOsiApproved"]
                id = item["licenseId"]
                break
        return html_url, isOsiApproved, id

    def lookup_license_by_name(self, lvalue, metric_id):
        # TODO - find simpler way to run fuzzy-based search over dict/json (e.g., regex)
        html_url = None
        isOsiApproved = False
        id = None
        self.logger.info(f"{metric_id} : License verification name through SPDX registry -: {lvalue}")
        # Levenshtein distance similarity ratio between two license name
        if lvalue:
            sim = [Levenshtein.ratio(lvalue.lower(), i) for i in self.fuji.SPDX_LICENSE_NAMES]
            if max(sim) > 0.85:
                index_max = max(range(len(sim)), key=sim.__getitem__)
                sim_license = self.fuji.SPDX_LICENSE_NAMES[index_max]
                found = next((item for item in self.fuji.SPDX_LICENSES if item["name"] == sim_license), None)
                self.logger.info("{}: Found SPDX license representation -: {}".format(metric_id, found["detailsUrl"]))
                # html_url = '.html'.join(found['detailsUrl'].rsplit('.json', 1))
                html_url = found["detailsUrl"].replace(".json", ".html")
                isOsiApproved = found["isOsiApproved"]
                id = found["licenseId"]
        return html_url, isOsiApproved, id

    def testLicenseMetadataElementAvailable(self):
        agnostic_test_name = "testLicenseMetadataElementAvailable"
        test_status = False
        test_id = self.metric_test_map[agnostic_test_name]
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            # TODO implement
            if test_id.startswith("FRSM"):
                self.logger.warning(
                    f"{self.metric_identifier} : Test for availability of license metadata is not implemented for FRSM."
                )
            test_score = self.getTestConfigScore(test_id)
            if self.license_info is not None and self.license_info != []:
                test_status = True
                self.logger.log(
                    self.fuji.LOG_SUCCESS, f"{self.metric_identifier} : Found licence information in metadata"
                )
                self.maturity = self.getTestConfigMaturity(test_id)
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned += test_score
            else:
                self.logger.warning(f"{self.metric_identifier} : License information unavailable in metadata")
        return test_status

    def testLicenseIsValidAndSPDXRegistered(self):
        agnostic_test_name = "testLicenseIsValidAndSPDXRegistered"
        test_status = False
        test_requirements = {}
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            if self.metric_tests[test_id].metric_test_requirements:
                test_requirements = self.metric_tests[test_id].metric_test_requirements[0]
            test_score = self.getTestConfigScore(test_id)
            test_required = []
            if test_requirements.get("required"):
                if isinstance(test_requirements.get("required"), list):
                    test_required = test_requirements.get("required")
                elif test_requirements.get("required").get("name"):
                    test_required = test_requirements.get("required").get("name")
                if not isinstance(test_required, list):
                    test_required = [test_required]

                self.logger.info(
                    "{0} : Will exclusively consider community specific licenses for {0} which are specified in metrics -: {1}".format(
                        test_id, test_requirements.get("required")
                    )
                )
            else:
                self.logger.info(
                    "{0} : Will consider all SPDX licenses as community specific licenses for {0} ".format(
                        self.metric_identifier,
                    )
                )
            if self.license_info:
                for license in self.license_info:
                    if test_required:
                        for rq_license_id in test_required:
                            if license.get("id"):
                                if fnmatch.fnmatch(license.get("id"), rq_license_id):
                                    test_status = True
                    else:
                        if license.get("valid"):
                            test_status = True
            else:
                self.logger.warning(
                    "{} : Skipping SPDX and community license verification since license information unavailable in metadata".format(
                        self.metric_identifier
                    )
                )

            if test_status:
                self.maturity = self.getTestConfigMaturity(test_id)
                self.score.earned += test_score
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")

        return test_status

    def testLicenseMetadataZenodo(self):
        """Licensing information is included in the Zenodo record and in a LICENSE.txt file included in the root directory of the source code deposited in Zenodo.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testLicenseMetadataZenodo"
        test_status = False
        test_id = self.metric_test_map[agnostic_test_name]
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for license information in Zenodo record and TXT in Zenodo is not implemented."
            )
        return test_status

    def evaluate(self):
        self.setLicenseDataAndOutput()

        self.result = License(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )

        license_status = "fail"
        if self.testLicenseMetadataElementAvailable():
            license_status = "pass"
        if self.testLicenseIsValidAndSPDXRegistered():
            license_status = "pass"
        if self.testLicenseMetadataZenodo():
            license_status = "pass"

        self.result.test_status = license_status
        self.result.output = self.output
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
