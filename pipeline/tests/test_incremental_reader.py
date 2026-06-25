from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import process_cowrie_ndjson
from process_cowrie_ndjson import (
    determine_read_position,
    file_identity,
    index_events,
    read_events,
)


def event_line(sequence: int) -> bytes:
    return (
        json.dumps(
            {
                "eventid": "cowrie.test",
                "session": f"session-{sequence}",
                "sequence": sequence,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def checkpoint_for(path: Path, offset: int, line_number: int) -> dict[str, object]:
    identity = file_identity(path)
    return {
        "source_key": "cowrie_ndjson",
        "file_device": identity.device,
        "file_inode": identity.inode,
        "fingerprint_hash": identity.fingerprint_hash,
        "fingerprint_bytes": identity.fingerprint_bytes,
        "byte_offset": offset,
        "line_number": line_number,
        "file_size": identity.size,
        "reset_count": 0,
    }


class IncrementalReaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "cowrie.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_append_reads_only_new_complete_lines(self) -> None:
        first = event_line(1)
        self.path.write_bytes(first)
        checkpoint = checkpoint_for(self.path, len(first), 1)

        with self.path.open("ab") as target:
            target.write(event_line(2))

        position = determine_read_position(self.path, checkpoint)
        batch = read_events(self.path, position.offset, position.line_number)

        self.assertIsNone(position.reset_reason)
        self.assertEqual(len(batch.events), 1)
        self.assertEqual(batch.events[0]["raw_document"]["sequence"], 2)
        self.assertEqual(batch.next_line_number, 2)

    def test_restart_keeps_existing_offset(self) -> None:
        content = event_line(1) + event_line(2)
        self.path.write_bytes(content)
        checkpoint = checkpoint_for(self.path, len(content), 2)

        position = determine_read_position(self.path, checkpoint)
        batch = read_events(self.path, position.offset, position.line_number)

        self.assertEqual(position.offset, len(content))
        self.assertIsNone(position.reset_reason)
        self.assertEqual(batch.events, [])

    def test_truncation_resets_to_start(self) -> None:
        original = event_line(1) + event_line(2)
        self.path.write_bytes(original)
        checkpoint = checkpoint_for(self.path, len(original), 2)
        self.path.write_bytes(event_line(3))

        position = determine_read_position(self.path, checkpoint)

        self.assertEqual(position.offset, 0)
        self.assertEqual(position.line_number, 0)
        self.assertEqual(position.reset_reason, "file_truncated")

    def test_replacement_with_different_prefix_resets_to_start(self) -> None:
        original = event_line(1)
        self.path.write_bytes(original)
        checkpoint = checkpoint_for(self.path, len(original), 1)
        replacement = event_line(9) + event_line(10)
        self.path.write_bytes(replacement)

        position = determine_read_position(self.path, checkpoint)

        self.assertEqual(position.offset, 0)
        self.assertEqual(position.reset_reason, "file_replaced")

    def test_partial_line_remains_pending(self) -> None:
        complete = event_line(1)
        partial = event_line(2).rstrip(b"\n")
        self.path.write_bytes(complete + partial)

        batch = read_events(self.path)

        self.assertEqual(len(batch.events), 1)
        self.assertEqual(batch.next_offset, len(complete))
        self.assertEqual(batch.next_line_number, 1)

    def test_invalid_complete_line_is_quarantined_and_skipped(self) -> None:
        valid = event_line(1)
        invalid = b'{"eventid":invalid}\n'
        self.path.write_bytes(valid + invalid + event_line(2))

        batch = read_events(self.path)

        self.assertEqual(len(batch.events), 2)
        self.assertEqual(len(batch.invalid_events), 1)
        self.assertEqual(batch.invalid_events[0].error_code, "invalid_json")
        self.assertEqual(batch.invalid_events[0].line_number, 2)
        self.assertEqual(batch.next_line_number, 3)

    def test_elasticsearch_transient_errors_are_retried(self) -> None:
        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return b'{"errors":false,"items":[]}'

        event = read_events(
            self._write(event_line(1))
        ).events[0]
        with (
            patch.object(process_cowrie_ndjson, "ensure_index"),
            patch.object(process_cowrie_ndjson.time, "sleep"),
            patch.object(
                process_cowrie_ndjson.request,
                "urlopen",
                side_effect=[URLError("temporary"), URLError("temporary"), Response()],
            ) as urlopen,
        ):
            indexed = index_events("http://elasticsearch:9200", "events", [event])

        self.assertEqual(indexed, 1)
        self.assertEqual(urlopen.call_count, 3)

    def _write(self, content: bytes) -> Path:
        self.path.write_bytes(content)
        return self.path


if __name__ == "__main__":
    unittest.main()
