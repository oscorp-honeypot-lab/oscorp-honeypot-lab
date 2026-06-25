#!/usr/bin/env python3
"""Private HTTP adapter for the OSCORP pipeline worker."""

from __future__ import annotations

import json
import os
import threading
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from process_cowrie_ndjson import execute_pipeline


MAX_REQUEST_BYTES = 64 * 1024
RUN_LOCK = threading.Lock()


def validate_request(payload: Any) -> tuple[dict[str, str] | None, str | None]:
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    allowed = {
        "contract_version",
        "request_id",
        "triggered_by",
        "mode",
        "source",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        return None, f"Unknown fields: {', '.join(unknown)}"
    if payload.get("contract_version") != "1.0":
        return None, "contract_version must be 1.0."

    try:
        request_id = str(uuid.UUID(str(payload.get("request_id"))))
    except (TypeError, ValueError, AttributeError):
        return None, "request_id must be a valid UUID."

    triggered_by = payload.get("triggered_by")
    if triggered_by not in {"n8n_manual", "n8n_schedule", "recovery"}:
        return None, "triggered_by is invalid."

    mode = payload.get("mode")
    if mode not in {"incremental", "recovery"}:
        return None, "mode is invalid."

    source = payload.get("source", "cowrie_ndjson")
    if source != "cowrie_ndjson":
        return None, "source must be cowrie_ndjson."

    return {
        "contract_version": "1.0",
        "request_id": request_id,
        "triggered_by": triggered_by,
        "mode": mode,
        "source": source,
    }, None


class PipelineWorkerHandler(BaseHTTPRequestHandler):
    server_version = "OSCORPPipelineWorker/1.0"

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self.send_json(
            HTTPStatus.OK,
            {
                "status": "ok",
                "contract_version": "1.0",
                "busy": RUN_LOCK.locked(),
            },
        )

    def do_POST(self) -> None:
        if self.path != "/runs":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self.send_json(
                HTTPStatus.LENGTH_REQUIRED,
                {"error": "content_length_required"},
            )
            return
        try:
            body_length = int(content_length)
        except ValueError:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_content_length"},
            )
            return
        if body_length < 0 or body_length > MAX_REQUEST_BYTES:
            self.send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "request_too_large"},
            )
            return

        try:
            payload = json.loads(self.rfile.read(body_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_json"},
            )
            return

        run_request, validation_error = validate_request(payload)
        if validation_error:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {
                    "error": "validation_error",
                    "message": validation_error,
                },
            )
            return

        if not RUN_LOCK.acquire(blocking=False):
            self.send_json(
                HTTPStatus.CONFLICT,
                {
                    "error": "worker_busy",
                    "message": "Another pipeline execution is already running.",
                },
            )
            return

        try:
            transport_error = False
            try:
                result = execute_pipeline(
                    run_request["request_id"],
                    triggered_by=run_request["triggered_by"],
                    mode=run_request["mode"],
                    source=run_request["source"],
                )
            except Exception as exc:
                transport_error = True
                result = {
                    "contract_version": "1.0",
                    "request_id": run_request["request_id"],
                    "run_id": None,
                    "status": "failed",
                    "events_read": 0,
                    "events_inserted": 0,
                    "events_indexed": 0,
                    "errors_count": 1,
                    "error_code": "worker_internal_error",
                    "error_detail": str(exc),
                }
        finally:
            RUN_LOCK.release()

        status = (
            HTTPStatus.INTERNAL_SERVER_ERROR
            if transport_error
            else HTTPStatus.OK
        )
        self.send_json(status, result)

    def send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(
            f"{self.address_string()} - {format % args}",
            flush=True,
        )


def main() -> None:
    host = os.environ.get("PIPELINE_WORKER_HOST", "0.0.0.0")
    port = int(os.environ.get("PIPELINE_WORKER_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), PipelineWorkerHandler)
    print(f"OSCORP pipeline worker listening on {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
