import os

from github import Github, Auth
from github.GithubException import RateLimitExceededException, UnknownObjectException
from configparser import ConfigParser

from fuji_server.helper.identifier_helper import IdentifierHelper

class GithubHarvester:   
    def __init__(self, id, host="https://github.com"):
        # Read Github API access token from config file.
        config = ConfigParser()
        config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../config/github.cfg'))
        auth_token = Auth.Token(config['ACCESS']['token'])
        self.id = id
        self.host = host
        if host != "https://github.com":
            base_url = f"{self.host}/api/v3"
            self.handle = Github(auth=auth_token, base_url=base_url)
        else:
            self.handle = Github(auth=auth_token)
        self.data = {}  # dictionary with all info

    def harvest(self):
        print("\n\n\n----------------------\nGitHub Harvest\n----------------------")
        # check if it's a URL or repo ID
        # NOTE: this should probably be handled by IdentifierHelper, but I don't understand that module yet.
        if self.id.count('/') > 1:  # URL
            self.url = self.id
            _, self.username, self.repo_name = self.id.rsplit("/", 2)
        else:  # repo ID
            self.username, self.repo_name = self.id.split("/")
            self.url = "/".join([self.endpoint, self.username, self.repo_name])
        self.repo_id = "/".join([self.username, self.repo_name])

        # access repo via GitHub API
        repo = self.handle.get_repo(self.repo_id)

        # harvesting
        license_file = repo.get_license()
        try:  # LICENSE
            license_file = repo.get_license()
            self.data['license'] = license_file.license.key
        except UnknownObjectException:
            pass

        print(self.data)
        print("----------------------\n\n\n")