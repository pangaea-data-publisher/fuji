# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import fnmatch
import re
from pathlib import Path

import idutils
import Levenshtein
import lxml.etree as ET

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.license import License
from fuji_server.models.license_output_inner import LicenseOutputInner


class FAIREvaluatorLicenseFile(FAIREvaluator):
    """
    A class to evaluate whether the software source code includes licensing information.
    A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will check the software and its documentation for the presence of a licence.

    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        self.set_metric(["FRSM-15-R1.1"])

        self.output = []
        self.license_info = []

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testLicenseIsValidAndSPDXRegistered": ["FRSM-15-R1.1-3"],
            "testLicenseFileAvailable": ["FRSM-15-R1.1-1"],
            "testLicenseFileAtRoot": ["FRSM-15-R1.1-CESSDA-1"],
            "testLicenseInHeaders": ["FRSM-15-R1.1-CESSDA-2"],
            "testLicenseForBundled": ["FRSM-15-R1.1-2"],
            "testBuildScriptChecksLicenseHeader": ["FRSM-15-R1.1-CESSDA-3"],
        }

    def setLicenseDataAndOutput(self):
        self.license_info = []
        # check for any recognised license files
        parsed_license_file_data = self.fuji.github_data.get("license_file")
        if parsed_license_file_data is not None and len(parsed_license_file_data) > 0:
            license_file_paths = [lf["path"] for lf in parsed_license_file_data]
        metadata_license = self.fuji.github_data.get("license")
        metadata_license_path = self.fuji.github_data.get("license_path")
        recognised_licenses = []
        if metadata_license is not None:
            for lfp in license_file_paths:  # only use metadata information if it matches a license file
                if lfp == metadata_license_path:
                    recognised_licenses.append(metadata_license)
        if recognised_licenses is not None and recognised_licenses != []:
            for license in recognised_licenses:
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

    def testLicenseFileAvailable(self):
        """License file is included.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testLicenseFileAvailable"
        test_status = False
        test_id = self.metric_test_map[agnostic_test_name]
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            parsed_license_file_data = self.fuji.github_data.get("license_file")
            if parsed_license_file_data is not None and len(parsed_license_file_data) > 0:
                license_file_paths = [lf["path"] for lf in parsed_license_file_data]
                test_status = True
                self.logger.log(
                    self.fuji.LOG_SUCCESS, f"{self.metric_identifier} : Found licence file: {license_file_paths}."
                )
                self.maturity = max(self.maturity, self.getTestConfigMaturity(test_id))
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned += test_score
            else:
                self.logger.warning(f"{self.metric_identifier} : Did not find licence file.")
        return test_status

    def testLicenseIsValidAndSPDXRegistered(self):
        """The software licensing information is in SPDX format, or other machine-readable form.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
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
            if self.license_info:  # license info is populated from recognised GitHub license (metadata)
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
                    "{} : Skipping SPDX and community license verification since no license information was recognised from metadata and no other mechanism of recognising licenses is currently available.".format(
                        self.metric_identifier
                    )
                )

            if test_status:
                self.maturity = max(self.maturity, self.getTestConfigMaturity(test_id))
                self.score.earned += test_score
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")

        return test_status

    def testLicenseTXTAtRoot(self):
        """Looks for license_path in self.fuji.github_data. Test passes if the license file is called LICENSE.txt and located at project root.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testLicenseFileAtRoot"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            license_file_paths = []
            parsed_license_file_data = self.fuji.github_data.get("license_file")
            if parsed_license_file_data is not None:
                license_file_paths += [lf["path"] for lf in parsed_license_file_data]
            for license_path in license_file_paths:
                if license_path is not None:
                    p = Path(license_path)
                    if p.stem == "LICENSE":
                        if str(p.parent) == ".":  # pass: LICENSE file at root
                            test_status = True
                            self.maturity = max(self.getTestConfigMaturity(test_id), self.maturity)
                            self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                            self.score.earned += test_score
                            if p.suffix == ".txt":
                                self.logger.log(
                                    self.fuji.LOG_SUCCESS,
                                    f"{self.metric_identifier} : Found LICENSE.txt at repository root ({test_id}).",
                                )
                            else:
                                self.logger.warning(
                                    f"{self.metric_identifier} : Found a license file at repository root, but the file suffix is not .txt ({test_id}). Test will still pass."
                                )
                            break
                        else:
                            self.logger.warning(
                                f"{self.metric_identifier} : Found a license file {license_path}, but it is not located at the root of the repository ({test_id})."
                            )
                    else:
                        self.logger.warning(
                            f"{self.metric_identifier} : Found a license file {license_path}, but the file name is not LICENSE ({test_id})."
                        )
            if not test_status:
                self.logger.warning(f"{self.metric_identifier} : Did not find a license file ({test_id}).")
        return test_status

    def testLicenseInHeaders(self):
        """Checks whether a sample of source code files include a license header. Fast-pass if the build script checks for license headers.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testLicenseInHeaders"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            test_requirements = self.metric_tests[test_id].metric_test_requirements[0]
            required_keywords = test_requirements["required"]["keywords"]
            # check whether CESSDA-3 was run and passed
            for tid in self.metric_test_map["testBuildScriptChecksLicenseHeader"]:
                if tid in self.metric_tests.keys() and self.metric_tests[tid].metric_test_status == "pass":
                    test_status = True
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        f"{self.metric_identifier} : Build script checks for license headers, so we can assume that all source files do contain license headers ({test_id}).",
                    )
            if not test_status:  # CESSDA-3 did not pass
                source_code_samples = self.fuji.github_data.get("source_code_samples")
                self.logger.info(
                    f"{self.metric_identifier} : Looking for any of {required_keywords} in source code samples ({test_id})."
                )
                if source_code_samples is not None:
                    license_headers_count = 0
                    for sample in source_code_samples:
                        header_region = "\n".join(sample["content"].decode("utf-8").splitlines()[:30]).lower()
                        for kw in required_keywords:
                            if kw in header_region:
                                license_headers_count += 1
                                break
                    if license_headers_count == len(source_code_samples):
                        test_status = True
                        self.logger.log(
                            self.fuji.LOG_SUCCESS,
                            f"{self.metric_identifier} : Sample of {len(source_code_samples)} source code files all contained a license header ({test_id}).",
                        )
                    else:
                        self.logger.warning(
                            f"{self.metric_identifier} : {license_headers_count} out of a sample of {len(source_code_samples)} source code files were found to contain a license header ({test_id})."
                        )
                else:
                    self.logger.warning(f"{self.metric_identifier} : No source code files found ({test_id}).")
            if test_status:  # test passed, update score and maturity
                self.maturity = max(self.getTestConfigMaturity(test_id), self.maturity)
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned += test_score
        return test_status

    def testLicenseForBundled(self):
        """Look for license information of bundled components. Not implemented.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testLicenseForBundled"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            self.logger.warning(
                f"{self.metric_identifier} : Test for license information of bundled components is not implemented ({test_id})."
            )
        return test_status

    def testBuildScriptChecksLicenseHeader(self):
        """Parses build script looking for command that ensures the presence of license headers.
        Currently only for Maven POM files and expects build to fail if license headers are missing.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testBuildScriptChecksLicenseHeader"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            test_requirements = self.metric_tests[test_id].metric_test_requirements[0]
            required_build_scripts = test_requirements["required"]["build_script"]
            if "maven_pom" in required_build_scripts:  # check Maven POM for plugin
                mvn_pom = self.fuji.github_data.get("maven_pom")
                if mvn_pom is not None:
                    content = mvn_pom[0]["content"]
                    # Check whether pom.xml uses license:check-file-header to validate license headers.
                    # See https://www.mojohaus.org/license-maven-plugin/check-file-header-mojo.html for more info.
                    root = ET.fromstring(content)
                    namespaces = root.nsmap
                    # look for plugin with artifactID license-maven-plugin
                    found_license_plugin = False
                    for plugin in root.iterfind(".//plugin", namespaces):
                        artifact_id = plugin.find("artifactId", namespaces)
                        if artifact_id is not None and artifact_id.text == "license-maven-plugin":
                            found_license_plugin = True
                            # too strict
                            # fail_on_missing_header = plugin.find("configuration/failOnMissingHeader", namespaces)
                            # if fail_on_missing_header is not None and fail_on_missing_header.text == "true":
                            test_status = True
                            self.logger.log(
                                self.fuji.LOG_SUCCESS,
                                f"{self.metric_identifier} : Maven POM checks for license headers in source files ({test_id}).",
                            )
                            self.maturity = max(self.getTestConfigMaturity(test_id), self.maturity)
                            self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                            self.score.earned += test_score
                            break
                    if not found_license_plugin:
                        self.logger.warning(
                            f"{self.metric_identifier} : Maven POM does not use license-maven-plugin (license:check-file-header) to check for license headers in source code files ({test_id})."
                        )
                else:
                    self.logger.warning(f"{self.metric_identifier} : Did not find a Maven POM file ({test_id}).")
            if any(e != "maven_pom" for e in required_build_scripts):
                self.logger.warning(f"{self.metric_identifier} : Unknown build script configured ({test_id}).")
        return test_status

    def evaluate(self):
        self.setLicenseDataAndOutput()

        self.result = License(
            id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
        )

        license_status = "fail"
        if self.testLicenseFileAvailable():
            license_status = "pass"
        if self.testLicenseIsValidAndSPDXRegistered():
            license_status = "pass"
        if self.testLicenseTXTAtRoot():
            license_status = "pass"
        if self.testLicenseForBundled():
            license_status = "pass"
        if self.testBuildScriptChecksLicenseHeader():
            license_status = "pass"
        if self.testLicenseInHeaders():
            license_status = "pass"

        self.result.test_status = license_status
        self.result.output = self.output
        self.result.metric_tests = self.metric_tests
        self.result.score = self.score
        self.result.maturity = self.maturity
