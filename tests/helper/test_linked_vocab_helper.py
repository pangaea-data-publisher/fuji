# SPDX-FileCopyrightText: 2020 PANGAEA (https://www.pangaea.de/)
#
# SPDX-License-Identifier: MIT

from fuji_server.helper.linked_vocab_helper import linked_vocab_helper


def test_linked_vocab_helper():
    linked_vocab_helper_ = linked_vocab_helper()
    assert not linked_vocab_helper_.linked_vocab_dict
    linked_vocab_helper_.set_linked_vocab_dict()
    assert linked_vocab_helper_.linked_vocab_dict
    # test entries from two different files are present
    assert "bioportal.aba-amb" in linked_vocab_helper_.linked_vocab_dict
    assert "bioregistry.3dmet" in linked_vocab_helper_.linked_vocab_dict
