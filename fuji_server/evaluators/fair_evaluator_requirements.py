# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import re

from fuji_server.evaluators.fair_evaluator import FAIREvaluator
from fuji_server.models.requirements import Requirements
from fuji_server.models.requirements_output import RequirementsOutput


class FAIREvaluatorRequirements(FAIREvaluator):
    """
    A class to evaluate whether the software describes what is required to use it (FRSM-13). A child class of FAIREvaluator.
    ...

    Methods
    ------
    evaluate()
        This method will evaluate machine-readable information that helps support the understanding of how the software is to be used.
    """

    def __init__(self, fuji_instance):
        FAIREvaluator.__init__(self, fuji_instance)
        metric = "FRSM-13-R1"
        self.set_metric(metric)

        # Create map from metric test names to class functions. This is necessary as functions may be reused for different metrics relating to licenses.
        self.metric_test_map = {  # overall map
            "testInstructions": ["FRSM-13-R1-1"],
            "testDependencies": ["FRSM-13-R1-2"],
            "testDependenciesBuildAutomatedChecks": ["FRSM-13-R1-CESSDA-1"],
            "testBadgeIncludedAutomatedDeploy": ["FRSM-13-R1-CESSDA-2"],
            "testBuildBadgeStatus": ["FRSM-13-R1-CESSDA-3"],
        }

    def nestedDataContainsKeyword(self, data, key):
        """Recursively check whether text data in nested structures (such as list and dict) contains a keyword.

        Args:
            data (list | dict): nested structure containing text data
            key (str): keyword to look for

        Raises:
            TypeError: argument data must be one of list or dict

        Returns:
            bool: True if key found somewhere in nested structure.
        """
        values = None
        if type(data) == list:
            values = data
        elif type(data) == dict:
            values = list(data.values())
        else:
            raise TypeError(
                f"Can only recursively scan lists and dictionaries, but received data of type {type(data)}."
            )
        for d in values:
            if type(d) == bytes:
                d = d.decode("utf-8")
            if type(d) == str:
                if key in d.lower():
                    return True
            else:
                try:
                    if self.nestedDataContainsKeyword(d, key):
                        return True
                except TypeError:
                    self.logger.warning(f"{self.metric_identifier}: scan of nested data failed for type {type(d)}.")
        return False

    def scanForKeywords(self, keywords, locations):
        """Scan GitHub harvesting results for keywords.

        Args:
            keywords (list<str>): list of keywords to look for
            locations (list<str>): list of locations to scan, used as keys for GitHub harvesting results

        Returns:
            dict<str, bool>: dictionary with keywords as keys and a boolean as value indicating whether the keyword was found in some location.
        """
        hit_dict = {k: False for k in keywords}
        keys_to_check = keywords
        # check each location (if available) for keywords
        for location in locations:
            for k in keys_to_check:
                content = self.fuji.github_data.get(location)
                if content is not None:
                    if type(content) == bytes:
                        content = content.decode("utf-8")
                    if type(content) == str:
                        if k in content.lower():
                            hit_dict[k] = True  # found keyword in location
                            keys_to_check.remove(k)  # stop looking, have found something for this key
                    else:
                        hit_dict[k] = self.nestedDataContainsKeyword(content, k)
        return hit_dict

    def testInstructions(self):
        """The software has build, installation and/or execution instructions.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testInstructions"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            test_requirements = self.metric_tests[test_id].metric_test_requirements[0]
            required_modality = test_requirements["modality"]
            required_keywords = test_requirements["required"]["keywords"]
            required_locations = test_requirements["required"]["location"]
            self.logger.info(
                f"{self.metric_identifier} : Looking for {required_modality} keywords {required_keywords} in {required_locations} ({test_id})."
            )
            hit_dict = self.scanForKeywords(required_keywords, required_locations)
            found_instructions = False
            if required_modality == "all":
                found_instructions = all(hit_dict.values())
            elif required_modality == "any":
                found_instructions = any(hit_dict.values())
            else:
                self.logger.warning(
                    f"{self.metric_identifier} : Unknown modality {required_modality} in test requirements ({test_id}). Choose 'all' or 'any'."
                )
            if found_instructions:
                test_status = True
                self.logger.log(
                    self.fuji.LOG_SUCCESS, f"{self.metric_identifier} : Found required keywords ({test_id})."
                )
                self.maturity = max(self.getTestConfigMaturity(test_id), self.maturity)
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned += test_score
            else:  # does not pass
                self.logger.warning(
                    f"{self.metric_identifier} : Did not find {required_modality} keywords {required_keywords} in {required_locations} ({test_id})."
                )
        return test_status

    def testDependencies(self):
        """Dependencies are provided in a machine-readable format and the building and installation of the software is automated.

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testDependencies"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            # Check for presence of machine-readable dependency files
            dependency_requirements = self.metric_tests[test_id].metric_test_requirements[0]
            assert (
                dependency_requirements["modality"] == "any"
            ), f"Found requirement modality {dependency_requirements['modality']}, please choose 'any' instead. Any other modality is too strict for this test layout."
            required_dependency_files = dependency_requirements["required"]["dependency_file"]
            self.logger.info(
                f"{self.metric_identifier} : Checking presence of any of {required_dependency_files} ({test_id})."
            )
            dependency_present = not set(self.fuji.github_data.keys()).isdisjoint(required_dependency_files)
            # Check for automated building and installation
            automation_requirements = self.metric_tests[test_id].metric_test_requirements[1]
            required_automation_locations = automation_requirements["required"]["automation_file"]
            required_automation_keywords = automation_requirements["required"]["automation_keywords"]
            self.logger.info(
                f"{self.metric_identifier} : Looking for {automation_requirements['modality']} keywords {required_automation_keywords} in {required_automation_locations} ({test_id})."
            )
            automation_hit_dict = self.scanForKeywords(required_automation_keywords, required_automation_locations)
            found_automation = False
            if automation_requirements["modality"] == "all":
                found_automation = all(automation_hit_dict.values())
            elif automation_requirements["modality"] == "any":
                found_automation = any(automation_hit_dict.values())
            else:
                self.logger.warning(
                    f"{self.metric_identifier} : Unknown modality {automation_requirements['modality']} in test requirements ({test_id}). Choose 'all' or 'any'."
                )
            if dependency_present and found_automation:  # pass
                test_status = True
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    f"{self.metric_identifier} : Found dependency and automation files ({test_id}).",
                )
                self.maturity = max(self.getTestConfigMaturity(test_id), self.maturity)
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned += test_score
            else:  # fail
                if not dependency_present:
                    self.logger.warning(
                        f"{self.metric_identifier} : Did not find any of {required_dependency_files} ({test_id})."
                    )
                if not found_automation:
                    self.logger.warning(
                        f"{self.metric_identifier} : Did not find {automation_requirements['modality']} keywords {required_automation_keywords} in {required_automation_locations} ({test_id})."
                    )
        return test_status

    def testDependenciesBuildAutomatedChecks(self):
        """Dependency information and build instructions are included in the README file.
        Linting and other relevant checks are present in the automated build and test process (e.g. via the Jenkinsfile).

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testDependenciesBuildAutomatedChecks"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            instructions_requirements = self.metric_tests[test_id].metric_test_requirements[0]
            required_instructions_locations = instructions_requirements["required"]["location"]
            required_instructions_keywords = instructions_requirements["required"]["keywords"]
            automation_requirements = self.metric_tests[test_id].metric_test_requirements[1]
            required_automation_locations = automation_requirements["required"]["automation_file"]
            required_automation_keywords = automation_requirements["required"]["automation_keywords"]
            self.logger.info(
                f"{self.metric_identifier} : Looking for {instructions_requirements['modality']} keywords {required_instructions_keywords} in {required_instructions_locations} ({test_id})."
            )
            # dependency info and build instruction in README
            instructions_hit_dict = self.scanForKeywords(
                required_instructions_keywords, required_instructions_locations
            )
            found_instructions = False
            if instructions_requirements["modality"] == "all":
                found_instructions = all(instructions_hit_dict.values())
            elif instructions_requirements["modality"] == "any":
                found_instructions = any(instructions_hit_dict.values())
            else:
                self.logger.warning(
                    f"{self.metric_identifier} : Unknown modality {instructions_requirements['modality']} in test requirements ({test_id}). Choose 'all' or 'any'."
                )
            # linting and other relevant checks present in automated build and test process
            self.logger.info(
                f"{self.metric_identifier} : Looking for {automation_requirements['modality']} keywords {required_automation_keywords} in {required_automation_locations} ({test_id})."
            )
            automation_hit_dict = self.scanForKeywords(required_automation_keywords, required_automation_locations)
            found_automation = False
            if automation_requirements["modality"] == "all":
                found_automation = all(automation_hit_dict.values())
            elif automation_requirements["modality"] == "any":
                found_automation = any(automation_hit_dict.values())
            else:
                self.logger.warning(
                    f"{self.metric_identifier} : Unknown modality {automation_requirements['modality']} in test requirements ({test_id}). Choose 'all' or 'any'."
                )
            if found_instructions and found_automation:  # pass
                test_status = True
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    f"{self.metric_identifier} : Found dependency, build and automation keywords ({test_id}).",
                )
                self.maturity = max(self.getTestConfigMaturity(test_id), self.maturity)
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned += test_score
            else:  # fail
                if not found_instructions:
                    self.logger.warning(
                        f"{self.metric_identifier} : Did not find {instructions_requirements['modality']} keywords {required_instructions_keywords} in {required_instructions_locations} ({test_id})."
                    )
                if not found_automation:
                    self.logger.warning(
                        f"{self.metric_identifier} : Did not find {automation_requirements['modality']} keywords {required_automation_keywords} in {required_automation_locations} ({test_id})."
                    )
        return test_status

    def testBadgeIncludedAutomatedDeploy(self):
        """The README file includes a badge that links to the automated build tool (Jenkins).
        Deployment to development and staging environments is automated (conditional on test results).

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testBadgeIncludedAutomatedDeploy"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            badge_requirements = self.metric_tests[test_id].metric_test_requirements[0]
            required_badge_link_keywords = badge_requirements["required"]["badge_link_keywords"]
            automation_requirements = self.metric_tests[test_id].metric_test_requirements[1]
            required_automation_locations = automation_requirements["required"]["automation_file"]
            required_automation_keywords = automation_requirements["required"]["automation_keywords"]
            # test for build badge linking to Jenkins
            found_build_badge = False
            badge_regex = r"\[!\[.*?\]\(.*?\)\]\((https?://[^)]+)\)"  # finds badges with links
            readme = self.fuji.github_data.get("README")
            if readme is not None:
                readme_raw = readme[0]["content"].decode("utf-8")
                badge_matches = re.findall(badge_regex, readme_raw)
                if len(badge_matches) > 0:
                    badge_hit_dict = {}
                    for badge_keyword in required_badge_link_keywords:
                        badge_hit_dict[badge_keyword] = self.nestedDataContainsKeyword(badge_matches, badge_keyword)
                    if badge_requirements["modality"] == "all":
                        found_build_badge = all(badge_hit_dict.values())
                    elif badge_requirements["modality"] == "any":
                        found_build_badge = any(badge_hit_dict.values())
                    else:
                        self.logger.warning(
                            f"{self.metric_identifier} : Unknown modality {badge_requirements['modality']} in test requirements ({test_id}). Choose 'all' or 'any'."
                        )
            # test for automated deployment
            self.logger.info(
                f"{self.metric_identifier} : Looking for {automation_requirements['modality']} keywords {required_automation_keywords} in {required_automation_locations} ({test_id})."
            )
            automation_hit_dict = self.scanForKeywords(required_automation_keywords, required_automation_locations)
            found_automation = False
            if automation_requirements["modality"] == "all":
                found_automation = all(automation_hit_dict.values())
            elif automation_requirements["modality"] == "any":
                found_automation = any(automation_hit_dict.values())
            else:
                self.logger.warning(
                    f"{self.metric_identifier} : Unknown modality {automation_requirements['modality']} in test requirements ({test_id}). Choose 'all' or 'any'."
                )
            # combine
            if found_build_badge and found_automation:
                test_status = True
                self.logger.log(
                    self.fuji.LOG_SUCCESS,
                    f"{self.metric_identifier} : Found build badge and automation keywords ({test_id}).",
                )
                self.maturity = max(self.getTestConfigMaturity(test_id), self.maturity)
                self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                self.score.earned += test_score
            else:  # fail
                if not found_build_badge:
                    self.logger.warning(f"{self.metric_identifier} : Did not find build badge in README ({test_id}).")
                if not found_automation:
                    self.logger.warning(
                        f"{self.metric_identifier} : Did not find {automation_requirements['modality']} keywords {required_automation_keywords} in {required_automation_locations} ({test_id})."
                    )
        return test_status

    def testBuildBadgeStatus(self):
        """The build badge indicates the status of the latest build (passing or failing).

        Returns:
            bool: True if the test was defined and passed. False otherwise.
        """
        agnostic_test_name = "testBuildBadgeStatus"
        test_status = False
        test_defined = False
        for test_id in self.metric_test_map[agnostic_test_name]:
            if self.isTestDefined(test_id):
                test_defined = True
                break
        if test_defined:
            test_score = self.getTestConfigScore(test_id)
            # test for build badge linking to Jenkins result
            # NOTE(km 28-2-24): stricter alternative requires the jenkins path to start with 'jenkins.'
            # badge_regex = r"\[!\[.*?\]\((https?://jenkins\.[^)]+/buildStatus/icon\?.*?)\)\]\((https?://jenkins\.[^)]+/job/[^)]+)\)"
            badge_regex = r"\[!\[.*?\]\((https?://[^)]+/buildStatus/icon\?.*?)\)\]\((https?://[^)]+/job/[^)]+)\)"
            readme = self.fuji.github_data.get("README")
            if readme is not None:
                readme_raw = readme[0]["content"].decode("utf-8")
                badge_matches = re.findall(badge_regex, readme_raw)
                if len(badge_matches) > 0:
                    test_status = True
                    self.logger.log(
                        self.fuji.LOG_SUCCESS,
                        f"{self.metric_identifier} : Found build badge indicating build status ({test_id}).",
                    )
                    self.maturity = max(self.getTestConfigMaturity(test_id), self.maturity)
                    self.setEvaluationCriteriumScore(test_id, test_score, "pass")
                    self.score.earned += test_score
                else:
                    self.logger.warning(
                        f"{self.metric_identifier} : Did not find build badge indicating the build status in README ({test_id})."
                    )
        return test_status

    def evaluate(self):
        if self.metric_identifier in self.metrics:
            self.result = Requirements(
                id=self.metric_number, metric_identifier=self.metric_identifier, metric_name=self.metric_name
            )
            self.output = RequirementsOutput()
            self.result.test_status = "fail"
            if self.testInstructions():
                self.result.test_status = "pass"
            if self.testDependencies():
                self.result.test_status = "pass"
            if self.testDependenciesBuildAutomatedChecks():
                self.result.test_status = "pass"
            if self.testBadgeIncludedAutomatedDeploy():
                self.result.test_status = "pass"
            if self.testBuildBadgeStatus():
                self.result.test_status = "pass"

            if self.result.test_status == "fail":
                self.score.earned = 0
                self.logger.warning(self.metric_identifier + " : Failed to check the software requirements.")

            self.result.score = self.score
            self.result.metric_tests = self.metric_tests
            self.result.output = self.output
            self.result.maturity = self.maturity
