# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import os
from configparser import ConfigParser

from github import Auth, Github
from github.GithubException import UnknownObjectException


class GithubHarvester:
    def __init__(self, id, logger, host="https://github.com"):
        # Read Github API access token from config file.
        config = ConfigParser()
        config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), "../config/github.ini"))
        token = config["ACCESS"]["token"]
        if token != "":
            auth = Auth.Token(token)
        else:  # empty token, so no authentication possible (rate limit will be much lower)
            auth = None
            print("Running in unauthenticated mode. Capabilities are limited.")
            self.logger.warning(
                "FRSM-09-A1 : Running in unauthenticated mode. Capabilities are limited."
            )  # TODO: would be better if it were a general warning!
        self.id = id
        self.host = host
        if host != "https://github.com":
            base_url = f"{self.host}/api/v3"
            self.handle = Github(auth=auth, base_url=base_url)
        else:
            self.handle = Github(auth=auth)
        self.logger = logger
        self.data = {}  # dictionary with all info

    def harvest(self):
        # check if it's a URL or repo ID
        # NOTE: this should probably be handled by IdentifierHelper, but I don't understand that module yet.
        if self.id.count("/") > 1:  # URL
            self.url = self.id
            _, self.username, self.repo_name = self.id.rsplit("/", 2)
        else:  # repo ID
            self.username, self.repo_name = self.id.split("/")
            self.url = "/".join([self.endpoint, self.username, self.repo_name])
        self.repo_id = "/".join([self.username, self.repo_name])

        # access repo via GitHub API
        try:
            repo = self.handle.get_repo(self.repo_id)
        except UnknownObjectException:
            print("Could not find repo.")
            self.logger.warning(
                "FRSM-09-A1 : Could not find repository on GitHub."
            )  # TODO: would be better if it were a general warning!
            return

        # harvesting
        try:  # LICENSE
            license_file = repo.get_license()
            self.data["license_path"] = license_file.path
            self.data["license"] = license_file.license.name
        except UnknownObjectException:
            pass

        try:  # Maven POM
            mvn_pom_file = repo.get_contents("pom.xml")
            self.data["mvn_pom"] = mvn_pom_file.decoded_content
        except UnknownObjectException:
            pass

        # identify source code (sample files in the main language used in the repo)
        repo_languages = repo.get_languages()
        if repo_languages != {}:
            self.data["languages"] = repo_languages
        main_source_code_language = repo.language
        if main_source_code_language is not None:
            self.data["main_language"] = main_source_code_language
            query = f" repo:{self.repo_id} language:{main_source_code_language}"  # needs the space in front as every query needs a string to match on
            source_code_files = self.handle.search_code(query)
            # extract code of up to n=5 files
            n = min(5, source_code_files.totalCount)
            source_code_samples = []
            for i in range(n):
                source_code_samples.append(
                    {
                        "path": source_code_files[i].path,
                        "language": main_source_code_language,
                        "content": source_code_files[i].decoded_content,
                    }
                )
            if len(source_code_samples) > 0:
                self.data["source_code_samples"] = source_code_samples

        # TODO: parse README (full), wiki (page names?), docs (???)

        # TODO: consider merging parts of the GitHub data with metadata?
