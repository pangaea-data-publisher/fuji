# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

import logging

import lxml.etree  # noqa: F401  request_helper uses lxml.etree but imports only lxml
import pytest

from fuji_server.helper.metadata_collector import MetadataFormats
from fuji_server.helper.request_helper import RequestHelper


@pytest.mark.parametrize(
    ("content_type", "expected_type", "expected_format"),
    [
        ("application/xml; charset=utf-8", "application/xml", MetadataFormats.XML),
        (
            "application/vnd.iso19139.metadata+xml; charset=utf-8",
            "application/vnd.iso19139.metadata+xml",
            MetadataFormats.XML,
        ),
        ("text/html; charset=utf-8", "text/html", MetadataFormats.HTML),
    ],
)
def test_content_type_parameters_are_ignored(content_type, expected_type, expected_format):
    helper = RequestHelper("https://example.org/metadata", logging.getLogger(__name__))
    helper.metric_id = "FsF-F2-01M"
    helper.response.url = "https://example.org/metadata"
    helper.response.content_type = content_type
    helper.response.content = b'<?xml version="1.0"?><root xmlns="https://example.org/ns"/>'

    helper.response.content_type = helper._detect_mime_type()
    parse_format, _ = helper._set_format_and_parsed_content()

    assert helper.response.content_type == expected_type
    assert parse_format == expected_format
