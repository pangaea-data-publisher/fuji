# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

"""
Tests for IdentifierHelper dPID (Decentralized Persistent Identifier) and
IPFS CID (InterPlanetary File System Content Identifier) support.
"""

import pytest

from fuji_server.helper.identifier_helper import IdentifierHelper


class TestDPID:
    """Tests for dPID (Decentralized Persistent Identifier) detection and extraction."""

    # Valid dPID identifiers
    @pytest.mark.parametrize(
        "identifier,expected_id",
        [
            # dpid:// scheme
            ("dpid://500", "500"),
            ("dpid://1", "1"),
            ("dpid://12345", "12345"),
            # dpid.org URLs
            ("https://dpid.org/500", "500"),
            ("https://dpid.org/1", "1"),
            ("http://dpid.org/500", "500"),
            # beta.dpid.org (production resolver)
            ("https://beta.dpid.org/500", "500"),
            ("https://beta.dpid.org/123", "123"),
            # dev.dpid.org
            ("https://dev.dpid.org/500", "500"),
            # With version suffix
            ("https://dpid.org/500/v1", "500"),
            ("https://dpid.org/500/v2", "500"),
        ],
    )
    def test_valid_dpid_detection(self, identifier, expected_id):
        """Test that valid dPID identifiers are correctly detected."""
        helper = IdentifierHelper(identifier)
        assert helper.is_dpid(), f"Expected {identifier} to be detected as dPID"
        assert helper.extract_dpid_id() == expected_id
        assert helper.preferred_schema == "dpid"
        assert "dpid" in helper.identifier_schemes
        assert helper.is_persistent is True
        assert helper.normalized_id == f"dpid://{expected_id}"
        assert helper.identifier_url == f"https://dpid.org/{expected_id}"

    # Invalid dPID identifiers - should NOT match
    @pytest.mark.parametrize(
        "identifier",
        [
            # Not dPID URLs
            "https://example.com/500",
            "https://doi.org/10.1234/test",
            "https://zenodo.org/record/123456",
            # Invalid dpid:// scheme formats
            "dpid://",
            "dpid://abc",  # non-numeric
            "dpid://beta/500",  # beta prefix not supported in scheme
            # Invalid dpid.org paths
            "https://dpid.org/",
            "https://dpid.org/abc",
            "https://dpid.org/test/path",
            # Other identifier types
            "10.1234/test.doi",
            "ark:/12345/test",
            "urn:isbn:0451450523",
            # IPFS CIDs (should not match dPID)
            "ipfs://bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",
            "https://ipfs.io/ipfs/QmTest123456789012345678901234567890123456",
        ],
    )
    def test_invalid_dpid_detection(self, identifier):
        """Test that non-dPID identifiers are not detected as dPID."""
        helper = IdentifierHelper(identifier)
        assert not helper.is_dpid(), f"Expected {identifier} to NOT be detected as dPID"

    def test_dpid_with_subdomains(self):
        """Test dPID detection with various subdomains."""
        # Anything ending in .dpid.org should be detected
        helper = IdentifierHelper("https://custom.dpid.org/500")
        assert helper.is_dpid()
        assert helper.extract_dpid_id() == "500"


class TestIPFSCID:
    """Tests for IPFS CID (Content Identifier) detection and extraction."""

    # Example CIDv0 (base58, starts with Qm, 46 chars)
    VALID_CIDV0 = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
    # Example CIDv1 (base32, starts with bafy)
    VALID_CIDV1 = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"

    @pytest.mark.parametrize(
        "identifier_template,cid_version",
        [
            # ipfs:// scheme
            ("ipfs://{cid}", "both"),
            ("ipfs://{cid}/path/to/file.txt", "both"),
            # Gateway URLs
            ("https://ipfs.io/ipfs/{cid}", "both"),
            ("https://ipfs.desci.com/ipfs/{cid}", "both"),
            ("https://pub.desci.com/ipfs/{cid}", "both"),
            ("https://dweb.link/ipfs/{cid}", "both"),
            ("https://cloudflare-ipfs.com/ipfs/{cid}", "both"),
            ("https://gateway.pinata.cloud/ipfs/{cid}", "both"),
            # With file paths
            ("https://ipfs.io/ipfs/{cid}/data/file.json", "both"),
            # Raw CIDs
            ("{cid}", "both"),
        ],
    )
    def test_valid_ipfs_cid_detection(self, identifier_template, cid_version):
        """Test that valid IPFS CIDs are correctly detected."""
        cids_to_test = []
        if cid_version in ["both", "v0"]:
            cids_to_test.append(self.VALID_CIDV0)
        if cid_version in ["both", "v1"]:
            cids_to_test.append(self.VALID_CIDV1)

        for cid in cids_to_test:
            identifier = identifier_template.format(cid=cid)
            helper = IdentifierHelper(identifier)
            assert helper.is_ipfs_cid(), f"Expected {identifier} to be detected as IPFS CID"
            assert helper.extract_ipfs_cid() == cid
            assert helper.preferred_schema == "ipfs"
            assert "ipfs" in helper.identifier_schemes
            assert helper.is_persistent is True
            assert helper.normalized_id == f"ipfs://{cid}"

    # Invalid IPFS identifiers - should NOT match
    @pytest.mark.parametrize(
        "identifier",
        [
            # Not IPFS URLs
            "https://example.com/file.txt",
            "https://doi.org/10.1234/test",
            # Invalid CID formats
            "ipfs://",
            "ipfs://invalid",
            "ipfs://Qm",  # Too short
            "ipfs://QmTooShort",  # Invalid length
            "ipfs://bafyshort",  # Too short for CIDv1
            # Other gateway URLs without valid CID
            "https://ipfs.io/ipfs/invalid",
            "https://ipfs.io/ipfs/",
            # dPIDs (should not match IPFS)
            "dpid://500",
            "https://dpid.org/500",
            # DOIs
            "10.1234/test.doi",
            "https://doi.org/10.1234/test",
            # Random strings
            "just-a-random-string",
            "12345678901234567890",
        ],
    )
    def test_invalid_ipfs_cid_detection(self, identifier):
        """Test that non-IPFS identifiers are not detected as IPFS CID."""
        helper = IdentifierHelper(identifier)
        assert not helper.is_ipfs_cid(), f"Expected {identifier} to NOT be detected as IPFS CID"

    def test_cidv0_format(self):
        """Test CIDv0 format validation (starts with Qm, 46 chars, base58)."""
        # Valid CIDv0
        helper = IdentifierHelper(self.VALID_CIDV0)
        assert helper.is_ipfs_cid()
        assert helper.extract_ipfs_cid() == self.VALID_CIDV0

        # Invalid CIDv0 - wrong prefix
        helper = IdentifierHelper("Xm" + self.VALID_CIDV0[2:])
        assert not helper.is_ipfs_cid()

        # Invalid CIDv0 - wrong length
        helper = IdentifierHelper(self.VALID_CIDV0[:40])
        assert not helper.is_ipfs_cid()

    def test_cidv1_format(self):
        """Test CIDv1 format validation (starts with bafy/bafk, base32)."""
        # Valid CIDv1 with bafy prefix
        helper = IdentifierHelper(self.VALID_CIDV1)
        assert helper.is_ipfs_cid()
        assert helper.extract_ipfs_cid() == self.VALID_CIDV1

        # Valid CIDv1 with bafk prefix
        bafk_cid = "bafkreigaknpexyvxt76zgkitavbwx6ejgfheup5oybpm77f3pxzrvwpfdi"
        helper = IdentifierHelper(bafk_cid)
        assert helper.is_ipfs_cid()
        assert helper.extract_ipfs_cid() == bafk_cid

    def test_ipfs_gateway_order(self):
        """Test that IPFS gateways are ordered correctly for DeSci content resolution."""
        # ipfs.desci.com should be first for best DeSci content resolution
        assert IdentifierHelper.IPFS_GATEWAYS[0] == "ipfs.desci.com"
        assert IdentifierHelper.IPFS_GATEWAYS[1] == "pub.desci.com"
        # dweb and ipfs.io should come after DeSci gateways
        assert "dweb.link" in IdentifierHelper.IPFS_GATEWAYS
        assert "ipfs.io" in IdentifierHelper.IPFS_GATEWAYS


class TestIdentifierHelperIntegration:
    """Integration tests to ensure dPID and IPFS don't conflict with other identifiers."""

    def test_doi_not_detected_as_dpid_or_ipfs(self):
        """DOIs should be detected as DOIs, not dPID or IPFS."""
        helper = IdentifierHelper("10.1234/test.doi")
        assert helper.preferred_schema == "doi"
        assert not helper.is_dpid()
        assert not helper.is_ipfs_cid()

    def test_handle_not_detected_as_dpid_or_ipfs(self):
        """Handles should be detected as handles, not dPID or IPFS."""
        helper = IdentifierHelper("hdl:10.1234/test")
        assert not helper.is_dpid()
        assert not helper.is_ipfs_cid()

    def test_ark_not_detected_as_dpid_or_ipfs(self):
        """ARKs should be detected as ARKs, not dPID or IPFS."""
        helper = IdentifierHelper("ark:/12345/test")
        assert helper.preferred_schema == "ark"
        assert not helper.is_dpid()
        assert not helper.is_ipfs_cid()

    def test_uuid_not_detected_as_dpid_or_ipfs(self):
        """UUIDs should not be detected as dPID or IPFS."""
        helper = IdentifierHelper("550e8400-e29b-41d4-a716-446655440000")
        assert helper.preferred_schema == "uuid"
        assert not helper.is_dpid()
        assert not helper.is_ipfs_cid()

    def test_w3id_not_detected_as_dpid_or_ipfs(self):
        """W3ID URLs should be detected as W3ID, not dPID or IPFS."""
        helper = IdentifierHelper("https://w3id.org/example/test")
        assert helper.preferred_schema == "w3id"
        assert not helper.is_dpid()
        assert not helper.is_ipfs_cid()

