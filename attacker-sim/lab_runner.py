#!/usr/bin/env python3
"""Lab runner HTTP server for OSCORP ThreatLab attacker-sim.

Exposes a minimal HTTP API (no external dependencies) to start and
monitor scenarios. Accepts only one concurrent execution.
"""

from __future__ import annotations

import json
import subprocess
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

ALLOWED_SCENARIOS = frozenset({"brute-force", "recon", "malware-download", "full"})
LOG_LIMIT = 50_000
HOST = "0.0.0.0"
PORT = 8888

_lock = threading.Lock()
_state: dict[str, Any] = {
    "status": "idle",
    "exit_code": None,
    "log": "",
}


def _run_scenario(scenario: str) -> None:
    global _state
    log_chunks: list[str] = []

    with _lock:
        _state = {"status": "running", "exit_code": None, "log": ""}

    try:
        proc = subprocess.Popen(
            ["/app/run_scenario.sh", scenario],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd="/app",
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log_chunks.append(line)
            combined = "".join(log_chunks)
            if len(combined) > LOG_LIMIT:
                log_chunks = [combined[-LOG_LIMIT:]]
            with _lock:
                _state["log"] = "".join(log_chunks)
        proc.wait()
        exit_code = proc.returncode
        status = "completed" if exit_code == 0 else "failed"
    except Exception as exc:
        exit_code = -1
        status = "failed"
        with _lock:
            _state["log"] = _state.get("log", "") + f"\n[lab-runner] error: {exc}"

    with _lock:
        _state["status"] = status
        _state["exit_code"] = exit_code


class LabRunnerHandler(BaseHTTPRequestHandler):
    server_version = "OSCORPLabRunner/1.0"

    def do_GET(self) -> None:
        if self.path != "/status":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        with _lock:
            snapshot = dict(_state)
        self._send_json(HTTPStatus.OK, snapshot)

    def do_POST(self) -> None:
        if self.path != "/run":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        content_length = self.headers.get("Content-Length")
        if not content_length:
            self._send_json(HTTPStatus.LENGTH_REQUIRED, {"error": "content_length_required"})
            return
        try:
            body = json.loads(self.rfile.read(int(content_length)).decode("utf-8"))
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        scenario = body.get("scenario", "")
        if scenario not in ALLOWED_SCENARIOS:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_scenario", "allowed": sorted(ALLOWED_SCENARIOS)},
            )
            return

        with _lock:
            if _state.get("status") in ("running",):
                self._send_json(HTTPStatus.CONFLICT, {"error": "already_running"})
                return
            _state["status"] = "starting"

        thread = threading.Thread(target=_run_scenario, args=(scenario,), daemon=True)
        thread.start()
        self._send_json(HTTPStatus.OK, {"status": "started", "scenario": scenario})

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"lab-runner: {format % args}", flush=True)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), LabRunnerHandler)
    print(f"OSCORP lab-runner listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
