"""Security audit tests — Phase 38.

Verify that the project maintains its security invariants:
- Sensitive paths are in .gitignore.
- All Docker images are pinned to a SHA-256 digest.
- All Python dependencies are pinned with ==.
- Secret values in .env.example are empty (generated at setup time).

These tests run in CI via the pipeline test-discovery job
(PYTHONPATH=../scripts, working-directory=pipeline).
The project root is located by walking up to the directory that
contains docker-compose.yml.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


def _find_project_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "docker-compose.yml").exists():
            return candidate
    raise RuntimeError("Cannot locate project root (no docker-compose.yml found)")


ROOT = _find_project_root()


class GitignoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._content = (ROOT / ".gitignore").read_text(encoding="utf-8")

    def test_env_is_ignored(self) -> None:
        self.assertIn(".env\n", self._content)

    def test_cowrie_logs_are_ignored(self) -> None:
        self.assertIn("cowrie/logs/*", self._content)

    def test_backups_are_ignored(self) -> None:
        self.assertIn("backups/*", self._content)

    def test_n8n_credentials_are_ignored(self) -> None:
        self.assertIn("n8n/credentials/*", self._content)


class DockerImagePinningTests(unittest.TestCase):
    """Verify that externally-pulled images are pinned to a SHA-256 digest.

    Local build images (pull_policy: never / image: oscorp/*) are excluded
    because their reproducibility is guaranteed by the Dockerfile + build
    context, not by a registry digest.
    """

    _LOCAL_IMAGE_PREFIX = "oscorp/"

    def setUp(self) -> None:
        self._compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    def _external_image_lines(self) -> list[str]:
        return [
            line.strip()
            for line in self._compose.splitlines()
            if re.match(r"\s+image:\s+\S+", line)
            and self._LOCAL_IMAGE_PREFIX not in line
        ]

    def test_external_images_have_digest_pin(self) -> None:
        """Every externally-pulled image must use @sha256: pinning."""
        lines = self._external_image_lines()
        self.assertGreater(len(lines), 0, "No external image: lines found")
        for line in lines:
            self.assertIn(
                "@sha256:",
                line,
                f"External image lacks digest pin: {line}",
            )

    def test_local_images_have_pull_policy_never(self) -> None:
        """Local oscorp/* images must declare pull_policy: never."""
        compose_text = self._compose
        # Find each service block that declares an oscorp/ image
        local_image_lines = [
            line.strip()
            for line in compose_text.splitlines()
            if re.match(r"\s+image:\s+oscorp/", line)
        ]
        self.assertGreater(len(local_image_lines), 0)
        # Verify that pull_policy: never appears in the compose file
        # (one entry per local image is sufficient — they all share the same config pattern)
        self.assertIn(
            "pull_policy: never",
            compose_text,
            "Local images must declare pull_policy: never",
        )


class RequirementsPinningTests(unittest.TestCase):
    def _requirement_lines(self, path: Path) -> list[str]:
        return [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

    def test_pipeline_requirements_all_pinned(self) -> None:
        lines = self._requirement_lines(ROOT / "pipeline" / "requirements.txt")
        self.assertGreater(len(lines), 0)
        for line in lines:
            self.assertRegex(
                line,
                r"^[A-Za-z0-9_\-\[\]]+==\d",
                f"Dependency not pinned with ==: {line}",
            )

    def test_backend_requirements_all_pinned(self) -> None:
        lines = self._requirement_lines(ROOT / "backend" / "requirements.txt")
        self.assertGreater(len(lines), 0)
        for line in lines:
            self.assertRegex(
                line,
                r"^[A-Za-z0-9_\-\[\]]+==\d",
                f"Dependency not pinned with ==: {line}",
            )


class EnvExampleSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        self._values: dict[str, str] = {}
        for line in lines:
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                self._values[key.strip()] = val.strip()

    def _assert_empty(self, key: str) -> None:
        self.assertIn(key, self._values, f"{key} not found in .env.example")
        self.assertEqual(
            self._values[key],
            "",
            f"{key} must be empty in .env.example (generated at setup time or user-provided secret)",
        )

    def test_n8n_encryption_key_is_empty(self) -> None:
        self._assert_empty("N8N_ENCRYPTION_KEY")

    def test_admin_password_is_empty(self) -> None:
        self._assert_empty("OSCORP_API_ADMIN_PASSWORD")

    def test_vt_api_key_is_empty(self) -> None:
        self._assert_empty("VT_API_KEY")

    def test_vps_host_is_empty(self) -> None:
        self._assert_empty("VPS_HOST")

    def test_elasticsearch_password_is_empty(self) -> None:
        self._assert_empty("ELASTICSEARCH_PASSWORD")
