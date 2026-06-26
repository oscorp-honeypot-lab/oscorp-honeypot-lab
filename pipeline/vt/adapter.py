from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from urllib.error import HTTPError, URLError

_VT_BASE = "https://www.virustotal.com/api/v3/files"


@dataclass(frozen=True, slots=True)
class VtResult:
    sha256: str
    malicious: int | None
    suspicious: int | None
    undetected: int | None
    harmless: int | None
    timeout: int | None
    last_analysis_date: int | None
    reputation: int | None
    error: str | None


def _empty(sha256: str, error: str) -> VtResult:
    return VtResult(
        sha256=sha256,
        malicious=None,
        suspicious=None,
        undetected=None,
        harmless=None,
        timeout=None,
        last_analysis_date=None,
        reputation=None,
        error=error,
    )


class VirusTotalAdapter:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("VT_API_KEY") or ""

    def query(self, sha256: str) -> VtResult:
        if not self._api_key:
            return _empty(sha256, "no_api_key")
        url = f"{_VT_BASE}/{sha256}"
        req = urllib.request.Request(url, headers={"x-apikey": self._api_key})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            attrs = data["data"]["attributes"]
            stats = attrs.get("last_analysis_stats", {})
            return VtResult(
                sha256=sha256,
                malicious=stats.get("malicious"),
                suspicious=stats.get("suspicious"),
                undetected=stats.get("undetected"),
                harmless=stats.get("harmless"),
                timeout=stats.get("timeout"),
                last_analysis_date=attrs.get("last_analysis_date"),
                reputation=attrs.get("reputation"),
                error=None,
            )
        except HTTPError as exc:
            if exc.code == 429:
                return _empty(sha256, "rate_limited")
            if exc.code == 404:
                return _empty(sha256, "not_found")
            return _empty(sha256, f"http_error:{exc.code}")
        except URLError as exc:
            return _empty(sha256, f"url_error:{exc.reason}")
