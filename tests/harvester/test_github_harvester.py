# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import logging

from fuji_server.harvester.github_harvester import GithubHarvester


def test_github_harvester():
    # this test just makes sure, that the GithubHarvester can read the "software_file.yaml" file
    id_ = "some-id"
    logger = logging.getLogger()
    harvester = GithubHarvester(id_, logger)
    assert harvester.files_map
