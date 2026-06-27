from __future__ import annotations

import json
import unittest
import uuid
from pathlib import Path

from pipeline_worker import validate_request


class ValidateRequestSourceModeTests(unittest.TestCase):
    def _base(self) -> dict:
        return {
            "contract_version": "1.0",
            "request_id": str(uuid.uuid4()),
            "triggered_by": "n8n_manual",
            "mode": "incremental",
            "source": "cowrie_ndjson",
        }

    def test_source_mode_lab_is_accepted(self) -> None:
        payload = {**self._base(), "source_mode": "lab"}
        result, error = validate_request(payload)
        self.assertIsNone(error)
        assert result is not None
        self.assertEqual(result["source_mode"], "lab")

    def test_source_mode_real_is_accepted(self) -> None:
        payload = {**self._base(), "source_mode": "real"}
        result, error = validate_request(payload)
        self.assertIsNone(error)
        assert result is not None
        self.assertEqual(result["source_mode"], "real")

    def test_source_mode_defaults_to_lab_when_omitted(self) -> None:
        result, error = validate_request(self._base())
        self.assertIsNone(error)
        assert result is not None
        self.assertEqual(result["source_mode"], "lab")

    def test_invalid_source_mode_returns_error(self) -> None:
        payload = {**self._base(), "source_mode": "staging"}
        result, error = validate_request(payload)
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("source_mode", error)

    def test_empty_string_source_mode_is_rejected(self) -> None:
        payload = {**self._base(), "source_mode": ""}
        result, error = validate_request(payload)
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_unknown_field_still_rejected_even_with_valid_source_mode(self) -> None:
        payload = {**self._base(), "source_mode": "lab", "extra_field": "x"}
        result, error = validate_request(payload)
        self.assertIsNone(result)
        self.assertIsNotNone(error)
        assert error is not None
        self.assertIn("extra_field", error)

    def test_request_contract_declares_source_mode(self) -> None:
        contract_path = (
            Path(__file__).resolve().parents[1]
            / "contracts"
            / "run-request.schema.json"
        )
        schema = json.loads(contract_path.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["properties"]["source_mode"]["enum"],
            ["lab", "real"],
        )
        self.assertEqual(
            schema["properties"]["source_mode"]["default"],
            "lab",
        )
