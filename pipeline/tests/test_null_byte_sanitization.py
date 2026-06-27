from __future__ import annotations

import hashlib
import json
import unittest

from process_cowrie_ndjson import normalize_event, strip_null_bytes


def _raw(event: dict) -> str:
    return json.dumps(event, separators=(",", ":"))


class StripNullBytesTests(unittest.TestCase):
    def test_strips_null_byte_from_string(self) -> None:
        self.assertEqual(strip_null_bytes("hel\x00lo"), "hello")

    def test_nested_dict_values_are_stripped(self) -> None:
        result = strip_null_bytes({"key": "val\x00ue", "nested": {"x": "\x00"}})
        self.assertEqual(result, {"key": "value", "nested": {"x": ""}})

    def test_list_values_are_stripped(self) -> None:
        result = strip_null_bytes(["a\x00b", "c"])
        self.assertEqual(result, ["ab", "c"])

    def test_non_string_types_are_unchanged(self) -> None:
        self.assertEqual(strip_null_bytes(42), 42)
        self.assertIsNone(strip_null_bytes(None))
        self.assertEqual(strip_null_bytes(3.14), 3.14)

    def test_clean_string_is_unchanged(self) -> None:
        self.assertEqual(strip_null_bytes("hello"), "hello")


class NormalizeEventNullByteTests(unittest.TestCase):
    def test_null_byte_in_raw_event_is_stripped(self) -> None:
        event = {
            "eventid": "cowrie.session.connect",
            "session": "abc123",
            "version": "SSH-2.0-\x00client",
        }
        result = normalize_event(_raw(event), event)
        self.assertEqual(result["raw_document"]["version"], "SSH-2.0-client")
        self.assertNotIn("\x00", json.dumps(result["raw_document"]))

    def test_null_byte_in_username_is_stripped(self) -> None:
        event = {
            "eventid": "cowrie.login.failed",
            "session": "abc123",
            "username": "root\x00",
            "password": "pass\x00word",
        }
        result = normalize_event(_raw(event), event)
        self.assertEqual(result["username"], "root")
        self.assertEqual(result["password"], "password")

    def test_null_byte_in_command_input_is_stripped(self) -> None:
        event = {
            "eventid": "cowrie.command.input",
            "session": "abc123",
            "input": "cat /etc/passwd\x00",
        }
        result = normalize_event(_raw(event), event)
        self.assertEqual(result["command_input"], "cat /etc/passwd")

    def test_event_hash_uses_original_raw_line(self) -> None:
        event = {"eventid": "cowrie.session.connect", "session": "s1", "version": "\x00"}
        raw = _raw(event)
        result = normalize_event(raw, event)
        expected_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        self.assertEqual(result["event_hash"], expected_hash)

    def test_clean_event_is_unchanged(self) -> None:
        event = {
            "eventid": "cowrie.login.failed",
            "session": "abc123",
            "username": "admin",
            "password": "1234",
        }
        result = normalize_event(_raw(event), event)
        self.assertEqual(result["username"], "admin")
        self.assertEqual(result["password"], "1234")
        self.assertEqual(result["raw_document"]["username"], "admin")
