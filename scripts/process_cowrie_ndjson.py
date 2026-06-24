#!/usr/bin/env python3
"""Process Cowrie NDJSON into PostgreSQL and Elasticsearch.

This script intentionally uses only the Python standard library plus Docker
Compose/psql so the lab can run on a clean Windows host without extra packages.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


EVENT_COLUMNS = [
    "event_hash",
    "event_uuid",
    "timestamp_evento",
    "eventid",
    "session_id",
    "sensor",
    "src_ip",
    "src_port",
    "username",
    "password",
    "command_input",
    "url",
    "shasum",
    "raw_event",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest Cowrie cowrie.json NDJSON into OSCORP storage.",
    )
    parser.add_argument("--log", default="cowrie/logs/cowrie.json")
    parser.add_argument("--postgres-service", default="postgres")
    parser.add_argument("--postgres-db", default="oscorp")
    parser.add_argument("--postgres-user", default="oscorp")
    parser.add_argument("--elasticsearch-url", default="http://localhost:9200")
    parser.add_argument("--elasticsearch-index", default="cowrie-events")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--skip-elasticsearch", action="store_true")
    parser.add_argument("--skip-postgres", action="store_true")
    return parser.parse_args()


def normalize_timestamp(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).astimezone(timezone.utc).isoformat()
    except ValueError:
        return str(value)


def normalize_event(raw_line: str, event: dict[str, Any]) -> dict[str, Any]:
    event_hash = hashlib.sha256(raw_line.encode("utf-8")).hexdigest()
    src_port = event.get("src_port")
    try:
        src_port = int(src_port) if src_port is not None else None
    except (TypeError, ValueError):
        src_port = None

    return {
        "event_hash": event_hash,
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
        "raw_event": json.dumps(event, ensure_ascii=False, separators=(",", ":")),
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


def csv_payload(events: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EVENT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for event in events:
        writer.writerow({key: event.get(key) for key in EVENT_COLUMNS})
    return buffer.getvalue()


def build_psql_script(events: list[dict[str, Any]]) -> str:
    columns_sql = ", ".join(EVENT_COLUMNS)
    return f"""
\\set ON_ERROR_STOP on
BEGIN;

ALTER TABLE eventos ADD COLUMN IF NOT EXISTS event_hash TEXT;
ALTER TABLE eventos ADD COLUMN IF NOT EXISTS event_uuid TEXT;
ALTER TABLE eventos DROP CONSTRAINT IF EXISTS eventos_event_uuid_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_eventos_event_hash ON eventos(event_hash);
CREATE INDEX IF NOT EXISTS idx_eventos_event_uuid ON eventos(event_uuid);

CREATE TEMP TABLE staging_events (
    event_hash TEXT,
    event_uuid TEXT,
    timestamp_evento TIMESTAMPTZ,
    eventid TEXT,
    session_id TEXT,
    sensor TEXT,
    src_ip TEXT,
    src_port INTEGER,
    username TEXT,
    password TEXT,
    command_input TEXT,
    url TEXT,
    shasum TEXT,
    raw_event JSONB
) ON COMMIT DROP;

COPY staging_events ({columns_sql}) FROM STDIN WITH (FORMAT csv, HEADER true);
{csv_payload(events)}\\.

WITH inserted AS (
    INSERT INTO eventos ({columns_sql})
    SELECT {columns_sql}
    FROM staging_events
    ON CONFLICT (event_hash) DO NOTHING
    RETURNING 1
)
INSERT INTO pipeline_runs (
    finished_at,
    events_read,
    events_inserted,
    events_indexed,
    alerts_sent,
    errors_count,
    status
)
SELECT
    NOW(),
    (SELECT COUNT(*) FROM staging_events),
    (SELECT COUNT(*) FROM inserted),
    0,
    0,
    0,
    'completed_postgres';

COMMIT;
"""


def run_postgres_ingest(args: argparse.Namespace, events: list[dict[str, Any]]) -> None:
    script = build_psql_script(events)
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        args.postgres_service,
        "psql",
        "-U",
        args.postgres_user,
        "-d",
        args.postgres_db,
    ]
    completed = subprocess.run(
        command,
        input=script,
        text=True,
        cwd=args.project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(completed.stdout)
    if completed.returncode != 0:
        raise RuntimeError("PostgreSQL ingest failed")


def update_pipeline_run_indexed(args: argparse.Namespace, indexed_count: int) -> None:
    sql = f"""
UPDATE pipeline_runs
SET
    finished_at = NOW(),
    events_indexed = {indexed_count},
    status = 'completed'
WHERE id = (
    SELECT id
    FROM pipeline_runs
    ORDER BY id DESC
    LIMIT 1
);
"""
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        args.postgres_service,
        "psql",
        "-U",
        args.postgres_user,
        "-d",
        args.postgres_db,
    ]
    completed = subprocess.run(
        command,
        input=sql,
        text=True,
        cwd=args.project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(completed.stdout)
    if completed.returncode != 0:
        raise RuntimeError("Pipeline run update failed")


def http_json(method: str, url: str, payload: Any | None = None) -> tuple[int, str]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=30) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body


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
    status, body = http_json("PUT", f"{base_url.rstrip('/')}/{index}", mapping)
    if status not in (200, 201, 400):
        raise RuntimeError(f"Elasticsearch index creation failed: {status} {body}")


def run_elasticsearch_ingest(args: argparse.Namespace, events: list[dict[str, Any]]) -> int:
    base_url = args.elasticsearch_url.rstrip("/")
    index = args.elasticsearch_index
    ensure_index(base_url, index)

    lines: list[str] = []
    for event in events:
        action = {"index": {"_index": index, "_id": event["event_hash"]}}
        doc = dict(event)
        doc["raw_event"] = json.loads(str(event["raw_event"]))
        lines.append(json.dumps(action, separators=(",", ":")))
        lines.append(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))

    bulk_body = ("\n".join(lines) + "\n").encode("utf-8")
    req = request.Request(
        f"{base_url}/_bulk",
        data=bulk_body,
        method="POST",
        headers={"Content-Type": "application/x-ndjson"},
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"Elasticsearch bulk request failed: {exc}") from exc

    if result.get("errors"):
        raise RuntimeError("Elasticsearch bulk ingest reported item errors")
    return len(events)


def main() -> int:
    args = parse_args()
    log_path = Path(args.log)
    if not log_path.exists():
        print(f"ERROR: log file not found: {log_path}", file=sys.stderr)
        return 1

    events = read_events(log_path)
    if not events:
        print("No events found.")
        return 0

    print(f"events_read={len(events)}")
    if not args.skip_postgres:
        run_postgres_ingest(args, events)
        print("postgres_ingest=ok")
    if not args.skip_elasticsearch:
        indexed = run_elasticsearch_ingest(args, events)
        print(f"elasticsearch_indexed={indexed}")
        if not args.skip_postgres:
            update_pipeline_run_indexed(args, indexed)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
