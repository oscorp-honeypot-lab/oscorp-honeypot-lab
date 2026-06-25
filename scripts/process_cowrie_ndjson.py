#!/usr/bin/env python3
"""Ingest Cowrie NDJSON into PostgreSQL and Elasticsearch."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

import psycopg
from psycopg.types.json import Jsonb


INSERT_EVENT_SQL = """
INSERT INTO eventos (
    event_hash,
    event_uuid,
    timestamp_evento,
    eventid,
    session_id,
    sensor,
    src_ip,
    src_port,
    username,
    password,
    command_input,
    url,
    shasum,
    raw_event
)
VALUES (
    %(event_hash)s,
    %(event_uuid)s,
    %(timestamp_evento)s,
    %(eventid)s,
    %(session_id)s,
    %(sensor)s,
    %(src_ip)s,
    %(src_port)s,
    %(username)s,
    %(password)s,
    %(command_input)s,
    %(url)s,
    %(shasum)s,
    %(raw_event)s
)
ON CONFLICT (event_hash) DO NOTHING
"""


def normalize_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return None


def normalize_event(raw_line: str, event: dict[str, Any]) -> dict[str, Any]:
    src_port = event.get("src_port")
    try:
        src_port = int(src_port) if src_port is not None else None
    except (TypeError, ValueError):
        src_port = None

    return {
        "event_hash": hashlib.sha256(raw_line.encode("utf-8")).hexdigest(),
        "event_uuid": event.get("uuid"),
        "timestamp_evento": normalize_timestamp(event.get("timestamp")),
        "eventid": event.get("eventid"),
        "session_id": event.get("session"),
        "sensor": event.get("sensor"),
        "src_ip": event.get("src_ip"),
        "src_port": src_port,
        "username": event.get("username"),
        "password": event.get("password"),
        "command_input": event.get("input"),
        "url": event.get("url"),
        "shasum": event.get("shasum"),
        "raw_event": Jsonb(event),
        "raw_document": event,
    }


def read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            raw_line = line.strip()
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid NDJSON at line {line_number}: {exc}") from exc
            events.append(normalize_event(raw_line, event))
    return events


def ensure_index(base_url: str, index: str) -> None:
    mapping = {
        "mappings": {
            "properties": {
                "event_hash": {"type": "keyword"},
                "event_uuid": {"type": "keyword"},
                "timestamp_evento": {"type": "date"},
                "eventid": {"type": "keyword"},
                "session_id": {"type": "keyword"},
                "sensor": {"type": "keyword"},
                "src_ip": {"type": "ip"},
                "src_port": {"type": "integer"},
                "username": {"type": "keyword"},
                "password": {"type": "keyword"},
                "command_input": {"type": "text"},
                "url": {"type": "keyword"},
                "shasum": {"type": "keyword"},
                "raw_event": {"type": "object", "enabled": True},
            }
        }
    }
    req = request.Request(
        f"{base_url.rstrip('/')}/{index}",
        data=json.dumps(mapping).encode("utf-8"),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=30):
            return
    except HTTPError as exc:
        if exc.code == 400:
            return
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Elasticsearch index creation failed: {exc.code} {body}"
        ) from exc


def index_events(
    base_url: str,
    index: str,
    events: list[dict[str, Any]],
) -> int:
    ensure_index(base_url, index)
    lines: list[str] = []
    for event in events:
        action = {"index": {"_index": index, "_id": event["event_hash"]}}
        document = {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in event.items()
            if key not in {"raw_event", "raw_document"}
        }
        document["raw_event"] = event["raw_document"]
        lines.append(json.dumps(action, separators=(",", ":")))
        lines.append(json.dumps(document, ensure_ascii=False, separators=(",", ":")))

    req = request.Request(
        f"{base_url.rstrip('/')}/_bulk?refresh=wait_for",
        data=("\n".join(lines) + "\n").encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-ndjson"},
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"Elasticsearch bulk request failed: {exc}") from exc

    if result.get("errors"):
        failed = [
            item
            for item in result.get("items", [])
            if item.get("index", {}).get("error")
        ]
        raise RuntimeError(f"Elasticsearch rejected {len(failed)} documents")
    return len(events)


def insert_events(
    connection: psycopg.Connection[Any],
    events: list[dict[str, Any]],
) -> int:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM eventos")
        before = int(cursor.fetchone()[0])
        cursor.executemany(INSERT_EVENT_SQL, events)
        cursor.execute("SELECT COUNT(*) FROM eventos")
        after = int(cursor.fetchone()[0])
    connection.commit()
    return after - before


def create_pipeline_run(
    connection: psycopg.Connection[Any],
    events_read: int,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pipeline_runs (events_read, status)
            VALUES (%s, 'running')
            RETURNING id
            """,
            (events_read,),
        )
        run_id = int(cursor.fetchone()[0])
    connection.commit()
    return run_id


def finish_pipeline_run(
    connection: psycopg.Connection[Any],
    run_id: int,
    inserted: int,
    indexed: int,
    status: str,
    errors: int = 0,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pipeline_runs
            SET
                finished_at = NOW(),
                events_inserted = %s,
                events_indexed = %s,
                errors_count = %s,
                status = %s
            WHERE id = %s
            """,
            (inserted, indexed, errors, status, run_id),
        )
    connection.commit()


def build_result(
    request_id: str,
    status: str,
    *,
    run_id: int | None = None,
    events_read: int = 0,
    events_inserted: int = 0,
    events_indexed: int = 0,
    errors_count: int = 0,
    error_code: str | None = None,
    error_detail: str | None = None,
) -> dict[str, Any]:
    return {
        "contract_version": "1.0",
        "request_id": request_id,
        "run_id": run_id,
        "status": status,
        "events_read": events_read,
        "events_inserted": events_inserted,
        "events_indexed": events_indexed,
        "errors_count": errors_count,
        "error_code": error_code,
        "error_detail": error_detail,
    }


def execute_pipeline(
    request_id: str,
    *,
    triggered_by: str,
    mode: str,
    source: str = "cowrie_ndjson",
) -> dict[str, Any]:
    if triggered_by not in {"n8n_manual", "n8n_schedule", "recovery"}:
        return build_result(
            request_id,
            "failed",
            errors_count=1,
            error_code="invalid_trigger",
            error_detail=f"Unsupported triggered_by value: {triggered_by}",
        )
    if mode not in {"incremental", "recovery"}:
        return build_result(
            request_id,
            "failed",
            errors_count=1,
            error_code="invalid_mode",
            error_detail=f"Unsupported mode: {mode}",
        )
    if source != "cowrie_ndjson":
        return build_result(
            request_id,
            "failed",
            errors_count=1,
            error_code="invalid_source",
            error_detail=f"Unsupported source: {source}",
        )

    log_path = Path(os.environ.get("COWRIE_LOG_PATH", "/files/cowrie/cowrie.json"))
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://oscorp:oscorp123@postgres:5432/oscorp",
    )
    elasticsearch_url = os.environ.get(
        "ELASTICSEARCH_URL",
        "http://elasticsearch:9200",
    )
    elasticsearch_index = os.environ.get(
        "ELASTICSEARCH_INDEX",
        "cowrie-events",
    )

    if not log_path.exists():
        return build_result(
            request_id,
            "failed",
            errors_count=1,
            error_code="source_not_found",
            error_detail=f"Log file not found: {log_path}",
        )

    try:
        events = read_events(log_path)
    except (OSError, ValueError) as exc:
        return build_result(
            request_id,
            "failed",
            errors_count=1,
            error_code="source_invalid",
            error_detail=str(exc),
        )
    try:
        connection = psycopg.connect(database_url)
    except psycopg.Error as exc:
        return build_result(
            request_id,
            "failed",
            events_read=len(events),
            errors_count=1,
            error_code="postgres_unavailable",
            error_detail=str(exc),
        )

    with connection:
        try:
            run_id = create_pipeline_run(connection, len(events))
        except psycopg.Error as exc:
            connection.rollback()
            return build_result(
                request_id,
                "failed",
                events_read=len(events),
                errors_count=1,
                error_code="postgres_run_create_failed",
                error_detail=str(exc),
            )

        inserted = 0
        indexed = 0
        try:
            if events:
                inserted = insert_events(connection, events)
                indexed = index_events(
                    elasticsearch_url,
                    elasticsearch_index,
                    events,
                )
            finish_pipeline_run(
                connection,
                run_id,
                inserted,
                indexed,
                "completed",
            )
        except Exception as exc:
            connection.rollback()
            try:
                finish_pipeline_run(
                    connection,
                    run_id,
                    inserted,
                    indexed,
                    "failed",
                    errors=1,
                )
            except psycopg.Error:
                connection.rollback()

            if isinstance(exc, psycopg.Error):
                error_code = "postgres_write_failed"
            elif "Elasticsearch" in str(exc):
                error_code = "elasticsearch_failed"
            else:
                error_code = "pipeline_internal_error"
            return build_result(
                request_id,
                "failed",
                run_id=run_id,
                events_read=len(events),
                events_inserted=inserted,
                events_indexed=indexed,
                errors_count=1,
                error_code=error_code,
                error_detail=str(exc),
            )

    return build_result(
        request_id,
        "completed",
        run_id=run_id,
        events_read=len(events),
        events_inserted=inserted,
        events_indexed=indexed,
    )


def main() -> int:
    request_id = str(uuid.uuid4())
    result = execute_pipeline(
        request_id,
        triggered_by="recovery",
        mode="recovery",
    )
    print(f"events_read={result['events_read']}")
    print(f"events_inserted={result['events_inserted']}")
    print(f"elasticsearch_indexed={result['events_indexed']}")
    print(f"status={result['status']}")
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    if result["status"] == "completed":
        return 0

    print(
        f"ERROR: {result['error_code']}: {result['error_detail']}",
        file=sys.stderr,
    )
    return {
        "invalid_trigger": 2,
        "invalid_mode": 2,
        "invalid_source": 2,
        "source_not_found": 3,
        "source_invalid": 3,
        "postgres_unavailable": 4,
        "postgres_run_create_failed": 4,
        "postgres_write_failed": 4,
        "elasticsearch_failed": 5,
    }.get(str(result["error_code"]), 10)


if __name__ == "__main__":
    raise SystemExit(main())
