#!/usr/bin/env python3
"""Ingest Cowrie NDJSON into PostgreSQL and Elasticsearch."""

from __future__ import annotations

import hashlib
import json
import os
import sys
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


def main() -> int:
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
        print(f"ERROR: log file not found: {log_path}", file=sys.stderr)
        return 1

    events = read_events(log_path)
    if not events:
        print("events_read=0")
        return 0

    print(f"events_read={len(events)}")
    with psycopg.connect(database_url) as connection:
        run_id = create_pipeline_run(connection, len(events))
        inserted = 0
        indexed = 0
        try:
            inserted = insert_events(connection, events)
            print(f"events_inserted={inserted}")
            indexed = index_events(
                elasticsearch_url,
                elasticsearch_index,
                events,
            )
            print(f"elasticsearch_indexed={indexed}")
            finish_pipeline_run(
                connection,
                run_id,
                inserted,
                indexed,
                "completed",
            )
        except Exception:
            finish_pipeline_run(
                connection,
                run_id,
                inserted,
                indexed,
                "failed",
                errors=1,
            )
            raise

    print("status=completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
