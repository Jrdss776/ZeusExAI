"""Focused tests for the Gmail IMAP connector."""

import json
from email.header import Header

from openjarvis.connectors.gmail_imap import _decode_subject, _header_text


def test_decode_subject_falls_back_for_unknown_8bit_charset():
    raw = "=?unknown-8bit?B?VGVzdGUg4Q==?="

    decoded = _decode_subject(raw)

    assert decoded.startswith("Teste")


def test_decode_subject_preserves_valid_encoded_words():
    assert _decode_subject("=?utf-8?B?T2zDoQ==?=") == "Olá"


def test_header_objects_are_normalized_to_json_safe_text():
    value = _header_text(Header(b"\xff", "unknown-8bit"))

    assert isinstance(value, str)
    json.dumps({"header": value})
