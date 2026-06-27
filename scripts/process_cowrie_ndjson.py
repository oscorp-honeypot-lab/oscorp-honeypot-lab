#!/usr/bin/env python3
"""Ingest Cowrie NDJSON into PostgreSQL and Elasticsearch."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

import psycopg
from psycopg.types.json import Jsonb

from alerts.dispatcher import dispatch_pending_alerts
from alerts.storage import generate_session_alerts
from alerts.telegram import TelegramAdapter
from geo.adapter import IpApiAdapter
from geo.elasticsearch import build_geo_lookup
from geo.enricher import enrich_session_ips
from reports.engine import generate_scheduled_reports
from risk.storage import recalculate_scores
from vt.adapter import VirusTotalAdapter
from vt.enricher import enrich_download_hashes


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
    raw_event,
    source_mode
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
    %(raw_event)s,
    %(source_mode)s
)
ON CONFLICT (event_hash) DO NOTHING
"""

SESSION_UPSERT_SQL = """
WITH targets(sensor, session_id) AS (
    SELECT * FROM UNNEST(%s::text[], %s::text[])
),
aggregated AS (
    SELECT
        COALESCE(e.sensor, 'unknown') || ':' || e.session_id AS session_key,
        e.session_id,
        COALESCE(e.sensor, 'unknown') AS sensor,
        (ARRAY_AGG(e.src_ip ORDER BY e.timestamp_evento, e.id)
            FILTER (WHERE e.src_ip IS NOT NULL))[1] AS src_ip,
        (ARRAY_AGG(e.src_port ORDER BY e.timestamp_evento, e.id)
            FILTER (WHERE e.src_port IS NOT NULL))[1] AS src_port,
        MIN(e.timestamp_evento) AS first_event_at,
        MAX(e.timestamp_evento) AS last_event_at,
        MIN(e.timestamp_evento) FILTER (
            WHERE e.eventid = 'cowrie.session.connect'
        ) AS connected_at,
        MAX(e.timestamp_evento) FILTER (
            WHERE e.eventid = 'cowrie.session.closed'
        ) AS closed_at,
        CASE
            WHEN BOOL_OR(e.eventid = 'cowrie.session.connect')
            AND BOOL_OR(e.eventid = 'cowrie.session.closed')
            THEN GREATEST(
                EXTRACT(EPOCH FROM (
                    MAX(e.timestamp_evento) FILTER (
                        WHERE e.eventid = 'cowrie.session.closed'
                    )
                    - MIN(e.timestamp_evento) FILTER (
                        WHERE e.eventid = 'cowrie.session.connect'
                    )
                )),
                0
            )
            ELSE NULL
        END AS duration_seconds,
        CASE
            WHEN BOOL_OR(e.eventid = 'cowrie.session.connect')
            AND BOOL_OR(e.eventid = 'cowrie.session.closed')
            THEN 'complete'
            WHEN BOOL_OR(e.eventid = 'cowrie.session.connect')
            THEN 'open'
            ELSE 'incomplete'
        END AS lifecycle_status,
        COUNT(*)::integer AS event_count,
        COUNT(*) FILTER (
            WHERE e.eventid = 'cowrie.login.success'
        )::integer AS login_success_count,
        COUNT(*) FILTER (
            WHERE e.eventid = 'cowrie.login.failed'
        )::integer AS login_failed_count,
        COUNT(*) FILTER (
            WHERE e.eventid = 'cowrie.command.input'
        )::integer AS command_count,
        COUNT(*) FILTER (
            WHERE e.eventid = 'cowrie.command.failed'
        )::integer AS command_failed_count,
        COUNT(*) FILTER (
            WHERE e.eventid = 'cowrie.session.file_download'
        )::integer AS download_count,
        (ARRAY_AGG(e.username ORDER BY e.timestamp_evento, e.id)
            FILTER (WHERE e.username IS NOT NULL))[1] AS first_username,
        (ARRAY_AGG(e.username ORDER BY e.timestamp_evento DESC, e.id DESC)
            FILTER (WHERE e.username IS NOT NULL))[1] AS last_username,
        BOOL_OR(e.eventid = 'cowrie.login.success') AS has_successful_login,
        BOOL_OR(e.eventid = 'cowrie.session.file_download') AS has_download,
        MIN(e.source_mode) AS source_mode
    FROM eventos e
    JOIN targets t
      ON t.sensor = COALESCE(e.sensor, 'unknown')
     AND t.session_id = e.session_id
    GROUP BY COALESCE(e.sensor, 'unknown'), e.session_id
)
INSERT INTO sessions (
    session_key, session_id, sensor, src_ip, src_port,
    first_event_at, last_event_at, connected_at, closed_at,
    duration_seconds, lifecycle_status, event_count,
    login_success_count, login_failed_count, command_count,
    command_failed_count, download_count, first_username,
    last_username, has_successful_login, has_download, source_mode
)
SELECT * FROM aggregated
ON CONFLICT (session_key) DO UPDATE
SET
    src_ip = EXCLUDED.src_ip,
    src_port = EXCLUDED.src_port,
    first_event_at = EXCLUDED.first_event_at,
    last_event_at = EXCLUDED.last_event_at,
    connected_at = EXCLUDED.connected_at,
    closed_at = EXCLUDED.closed_at,
    duration_seconds = EXCLUDED.duration_seconds,
    lifecycle_status = EXCLUDED.lifecycle_status,
    event_count = EXCLUDED.event_count,
    login_success_count = EXCLUDED.login_success_count,
    login_failed_count = EXCLUDED.login_failed_count,
    command_count = EXCLUDED.command_count,
    command_failed_count = EXCLUDED.command_failed_count,
    download_count = EXCLUDED.download_count,
    first_username = EXCLUDED.first_username,
    last_username = EXCLUDED.last_username,
    has_successful_login = EXCLUDED.has_successful_login,
    has_download = EXCLUDED.has_download,
    updated_at = NOW()
    -- source_mode intentionally omitted: once set, never changed
"""

FINGERPRINT_BYTES = 4096
ELASTICSEARCH_MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1


@dataclass(frozen=True)
class FileIdentity:
    device: int
    inode: int
    fingerprint_hash: str
    fingerprint_bytes: int
    size: int


@dataclass(frozen=True)
class ReadBatch:
    events: list[dict[str, Any]]
    invalid_events: list["InvalidEvent"]
    next_offset: int
    next_line_number: int
    identity: FileIdentity


@dataclass(frozen=True)
class ReadPosition:
    offset: int
    line_number: int
    reset_reason: str | None
    identity: FileIdentity


@dataclass(frozen=True)
class InvalidEvent:
    line_number: int
    byte_offset: int
    error_code: str
    error_detail: str
    raw_line: str


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


def file_identity(
    path: Path,
    fingerprint_bytes: int | None = None,
) -> FileIdentity:
    stat = path.stat()
    sample_size = min(
        stat.st_size,
        FINGERPRINT_BYTES if fingerprint_bytes is None else fingerprint_bytes,
    )
    with path.open("rb") as source:
        sample = source.read(sample_size)
    return FileIdentity(
        device=stat.st_dev,
        inode=stat.st_ino,
        fingerprint_hash=hashlib.sha256(sample).hexdigest(),
        fingerprint_bytes=sample_size,
        size=stat.st_size,
    )


def read_events(
    path: Path,
    start_offset: int = 0,
    start_line_number: int = 0,
) -> ReadBatch:
    events: list[dict[str, Any]] = []
    invalid_events: list[InvalidEvent] = []
    next_offset = start_offset
    line_number = start_line_number
    with path.open("rb") as source:
        source.seek(start_offset)
        while True:
            line_start = source.tell()
            line = source.readline()
            if not line:
                break
            if not line.endswith(b"\n"):
                next_offset = line_start
                break
            line_number += 1
            next_offset = source.tell()
            try:
                raw_line = line.decode("utf-8").strip()
            except UnicodeDecodeError as exc:
                invalid_events.append(
                    InvalidEvent(
                        line_number=line_number,
                        byte_offset=line_start,
                        error_code="invalid_utf8",
                        error_detail=str(exc),
                        raw_line=line.decode("utf-8", errors="replace").strip(),
                    )
                )
                continue
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                invalid_events.append(
                    InvalidEvent(
                        line_number=line_number,
                        byte_offset=line_start,
                        error_code="invalid_json",
                        error_detail=str(exc),
                        raw_line=raw_line,
                    )
                )
                continue
            if not isinstance(event, dict):
                invalid_events.append(
                    InvalidEvent(
                        line_number=line_number,
                        byte_offset=line_start,
                        error_code="invalid_event_shape",
                        error_detail="Cowrie event must be a JSON object.",
                        raw_line=raw_line,
                    )
                )
                continue
            events.append(normalize_event(raw_line, event))
        stat = os.fstat(source.fileno())
        fingerprint_bytes = min(next_offset, FINGERPRINT_BYTES)
        source.seek(0)
        fingerprint = hashlib.sha256(source.read(fingerprint_bytes)).hexdigest()
    return ReadBatch(
        events=events,
        invalid_events=invalid_events,
        next_offset=next_offset,
        next_line_number=line_number,
        identity=FileIdentity(
            device=stat.st_dev,
            inode=stat.st_ino,
            fingerprint_hash=fingerprint,
            fingerprint_bytes=fingerprint_bytes,
            size=stat.st_size,
        ),
    )


def load_checkpoint(
    connection: psycopg.Connection[Any],
    source_key: str,
) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                source_key,
                file_device,
                file_inode,
                fingerprint_hash,
                fingerprint_bytes,
                byte_offset,
                line_number,
                file_size,
                reset_count
            FROM pipeline_checkpoints
            WHERE source_key = %s
            """,
            (source_key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [description.name for description in cursor.description]
    return dict(zip(columns, row, strict=True))


def determine_read_position(
    path: Path,
    checkpoint: dict[str, Any] | None,
) -> ReadPosition:
    current = file_identity(path)
    if checkpoint is None:
        return ReadPosition(0, 0, None, current)

    offset = int(checkpoint["byte_offset"])
    if current.size < offset:
        return ReadPosition(0, 0, "file_truncated", current)

    fingerprint_bytes = int(checkpoint["fingerprint_bytes"])
    comparable = file_identity(path, fingerprint_bytes)
    if comparable.fingerprint_hash != checkpoint["fingerprint_hash"]:
        return ReadPosition(0, 0, "file_replaced", current)

    stored_identity = FileIdentity(
        device=current.device,
        inode=current.inode,
        fingerprint_hash=str(checkpoint["fingerprint_hash"]),
        fingerprint_bytes=fingerprint_bytes,
        size=current.size,
    )
    return ReadPosition(
        offset,
        int(checkpoint["line_number"]),
        None,
        stored_identity,
    )


_GEO_POINT_MAPPING = {"src_location": {"type": "geo_point"}}


def _update_index_geo_mapping(base_url: str, index: str) -> None:
    """Add src_location geo_point to an existing index (idempotent)."""
    req = request.Request(
        f"{base_url.rstrip('/')}/{index}/_mapping",
        data=json.dumps({"properties": _GEO_POINT_MAPPING}).encode("utf-8"),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=30):
            pass
    except (HTTPError, URLError):
        pass


def ensure_index(base_url: str, index: str) -> None:
    properties = {
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
        **_GEO_POINT_MAPPING,
    }
    req = request.Request(
        f"{base_url.rstrip('/')}/{index}",
        data=json.dumps({"mappings": {"properties": properties}}).encode("utf-8"),
        method="PUT",
        headers={"Content-Type": "application/json"},
    )
    last_error: Exception | None = None
    for attempt in range(1, ELASTICSEARCH_MAX_ATTEMPTS + 1):
        try:
            with request.urlopen(req, timeout=30):
                return
        except HTTPError as exc:
            if exc.code == 400:
                _update_index_geo_mapping(base_url, index)
                return
            last_error = exc
            if exc.code < 500 and exc.code != 429:
                break
        except URLError as exc:
            last_error = exc
        if attempt < ELASTICSEARCH_MAX_ATTEMPTS:
            time.sleep(RETRY_DELAY_SECONDS * attempt)

    if isinstance(last_error, HTTPError):
        body = last_error.read().decode("utf-8", errors="replace")
        detail = f"{last_error.code} {body}"
    else:
        detail = str(last_error)
    raise RuntimeError(
        "Elasticsearch index creation failed after "
        f"{ELASTICSEARCH_MAX_ATTEMPTS} attempts: {detail}"
    ) from last_error


def index_events(
    base_url: str,
    index: str,
    events: list[dict[str, Any]],
    geo_lookup: dict[str, dict[str, float]] | None = None,
) -> int:
    ensure_index(base_url, index)
    lookup = geo_lookup or {}
    lines: list[str] = []
    for event in events:
        action = {"index": {"_index": index, "_id": event["event_hash"]}}
        document = {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in event.items()
            if key not in {"raw_event", "raw_document"}
        }
        document["raw_event"] = event["raw_document"]
        src_ip = event.get("src_ip")
        if src_ip and src_ip in lookup:
            document["src_location"] = lookup[src_ip]
        lines.append(json.dumps(action, separators=(",", ":")))
        lines.append(json.dumps(document, ensure_ascii=False, separators=(",", ":")))

    req = request.Request(
        f"{base_url.rstrip('/')}/_bulk?refresh=wait_for",
        data=("\n".join(lines) + "\n").encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-ndjson"},
    )
    result: dict[str, Any] | None = None
    last_error: Exception | None = None
    for attempt in range(1, ELASTICSEARCH_MAX_ATTEMPTS + 1):
        try:
            with request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as exc:
            last_error = exc
            if exc.code < 500 and exc.code != 429:
                break
        except URLError as exc:
            last_error = exc
        if attempt < ELASTICSEARCH_MAX_ATTEMPTS:
            time.sleep(RETRY_DELAY_SECONDS * attempt)

    if result is None:
        raise RuntimeError(
            "Elasticsearch bulk request failed after "
            f"{ELASTICSEARCH_MAX_ATTEMPTS} attempts: {last_error}"
        ) from last_error

    if result.get("errors"):
        failed = [
            item
            for item in result.get("items", [])
            if item.get("index", {}).get("error")
        ]
        raise RuntimeError(f"Elasticsearch rejected {len(failed)} documents")
    return len(events)


def save_event_errors(
    connection: psycopg.Connection[Any],
    *,
    run_id: int,
    source_key: str,
    invalid_events: list[InvalidEvent],
) -> None:
    if not invalid_events:
        return
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO pipeline_event_errors (
                run_id,
                source_key,
                line_number,
                byte_offset,
                error_code,
                error_detail,
                raw_line
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    run_id,
                    source_key,
                    item.line_number,
                    item.byte_offset,
                    item.error_code,
                    item.error_detail,
                    item.raw_line,
                )
                for item in invalid_events
            ],
        )


def insert_events(
    connection: psycopg.Connection[Any],
    events: list[dict[str, Any]],
    source_mode: str = "lab",
) -> int:
    tagged = [{**event, "source_mode": source_mode} for event in events]
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM eventos")
        before = int(cursor.fetchone()[0])
        cursor.executemany(INSERT_EVENT_SQL, tagged)
        cursor.execute("SELECT COUNT(*) FROM eventos")
        after = int(cursor.fetchone()[0])
    connection.commit()
    return after - before


def refresh_sessions(
    connection: psycopg.Connection[Any],
    events: list[dict[str, Any]],
) -> tuple[str, ...]:
    session_pairs = sorted(
        {
            (
                str(event.get("sensor") or "unknown"),
                str(event["session_id"]),
            )
            for event in events
            if event.get("session_id")
        }
    )
    if not session_pairs:
        return ()
    sensors = [pair[0] for pair in session_pairs]
    session_ids = [pair[1] for pair in session_pairs]
    with connection.cursor() as cursor:
        cursor.execute(SESSION_UPSERT_SQL, (sensors, session_ids))
    connection.commit()
    return tuple(f"{sensor}:{session_id}" for sensor, session_id in session_pairs)


def create_pipeline_run(
    connection: psycopg.Connection[Any],
    events_read: int,
    *,
    request_id: str,
    triggered_by: str,
    source_key: str,
    mode: str,
    source_offset_start: int,
    checkpoint_reset_reason: str | None,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pipeline_runs (
                events_read,
                status,
                source_key,
                mode,
                source_offset_start,
                checkpoint_reset_reason,
                request_id,
                triggered_by
            )
            VALUES (%s, 'running', %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                events_read,
                source_key,
                mode,
                source_offset_start,
                checkpoint_reset_reason,
                request_id,
                triggered_by,
            ),
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
    source_offset_end: int | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
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
                status = %s,
                source_offset_end = %s,
                error_code = %s,
                error_detail = %s
            WHERE id = %s
            """,
            (
                inserted,
                indexed,
                errors,
                status,
                source_offset_end,
                error_code,
                error_detail,
                run_id,
            ),
        )
    connection.commit()


def load_pipeline_run_by_request(
    connection: psycopg.Connection[Any],
    request_id: str,
) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                id,
                status,
                events_read,
                events_inserted,
                events_indexed,
                errors_count,
                error_code,
                error_detail,
                source_offset_start,
                source_offset_end,
                checkpoint_reset_reason
            FROM pipeline_runs
            WHERE request_id = %s
            """,
            (request_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        columns = [description.name for description in cursor.description]
        cursor.execute(
            """
            UPDATE pipeline_runs
            SET attempt_count = attempt_count + 1
            WHERE request_id = %s
            """,
            (request_id,),
        )
    connection.commit()
    return dict(zip(columns, row, strict=True))


def reopen_pipeline_run(
    connection: psycopg.Connection[Any],
    *,
    run_id: int,
    events_read: int,
    source_offset_start: int,
    checkpoint_reset_reason: str | None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE pipeline_runs
            SET
                started_at = NOW(),
                finished_at = NULL,
                status = 'running',
                events_read = %s,
                events_inserted = 0,
                events_indexed = 0,
                errors_count = 0,
                error_code = NULL,
                error_detail = NULL,
                source_offset_start = %s,
                source_offset_end = NULL,
                checkpoint_reset_reason = %s
            WHERE id = %s
            """,
            (
                events_read,
                source_offset_start,
                checkpoint_reset_reason,
                run_id,
            ),
        )
    connection.commit()


def save_checkpoint(
    connection: psycopg.Connection[Any],
    *,
    source_key: str,
    identity: FileIdentity,
    batch: ReadBatch,
    run_id: int,
    reset_reason: str | None,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO pipeline_checkpoints (
                source_key,
                file_device,
                file_inode,
                fingerprint_hash,
                fingerprint_bytes,
                byte_offset,
                line_number,
                file_size,
                last_run_id,
                reset_count,
                last_reset_reason,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (source_key) DO UPDATE
            SET
                file_device = EXCLUDED.file_device,
                file_inode = EXCLUDED.file_inode,
                fingerprint_hash = EXCLUDED.fingerprint_hash,
                fingerprint_bytes = EXCLUDED.fingerprint_bytes,
                byte_offset = EXCLUDED.byte_offset,
                line_number = EXCLUDED.line_number,
                file_size = EXCLUDED.file_size,
                last_run_id = EXCLUDED.last_run_id,
                reset_count = pipeline_checkpoints.reset_count
                    + CASE WHEN EXCLUDED.last_reset_reason IS NULL THEN 0 ELSE 1 END,
                last_reset_reason = COALESCE(
                    EXCLUDED.last_reset_reason,
                    pipeline_checkpoints.last_reset_reason
                ),
                updated_at = NOW()
            """,
            (
                source_key,
                identity.device,
                identity.inode,
                identity.fingerprint_hash,
                identity.fingerprint_bytes,
                batch.next_offset,
                batch.next_line_number,
                identity.size,
                run_id,
                1 if reset_reason else 0,
                reset_reason,
            ),
        )


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
    source_offset_start: int = 0,
    source_offset_end: int = 0,
    checkpoint_reset_reason: str | None = None,
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
        "source_offset_start": source_offset_start,
        "source_offset_end": source_offset_end,
        "checkpoint_reset_reason": checkpoint_reset_reason,
    }


def execute_pipeline(
    request_id: str,
    *,
    triggered_by: str,
    mode: str,
    source: str = "cowrie_ndjson",
    source_mode: str = "lab",
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
    if source_mode not in {"lab", "real"}:
        return build_result(
            request_id,
            "failed",
            errors_count=1,
            error_code="invalid_source_mode",
            error_detail=f"Unsupported source_mode: {source_mode}",
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
        connection = psycopg.connect(database_url)
    except psycopg.Error as exc:
        return build_result(
            request_id,
            "failed",
            errors_count=1,
            error_code="postgres_unavailable",
            error_detail=str(exc),
        )

    with connection:
        existing_run = load_pipeline_run_by_request(connection, request_id)
        if existing_run is not None and existing_run["status"] in {
            "completed",
            "completed_with_errors",
        }:
            return build_result(
                request_id,
                str(existing_run["status"]),
                run_id=int(existing_run["id"]),
                events_read=int(existing_run["events_read"]),
                events_inserted=int(existing_run["events_inserted"]),
                events_indexed=int(existing_run["events_indexed"]),
                errors_count=int(existing_run["errors_count"]),
                error_code=existing_run["error_code"],
                error_detail=existing_run["error_detail"],
                source_offset_start=int(existing_run["source_offset_start"] or 0),
                source_offset_end=int(existing_run["source_offset_end"] or 0),
                checkpoint_reset_reason=existing_run[
                    "checkpoint_reset_reason"
                ],
            )

        try:
            if mode == "incremental":
                checkpoint = load_checkpoint(connection, source)
                position = determine_read_position(log_path, checkpoint)
            else:
                position = ReadPosition(
                    offset=0,
                    line_number=0,
                    reset_reason=None,
                    identity=file_identity(log_path),
                )
            batch = read_events(
                log_path,
                position.offset,
                position.line_number,
            )
        except psycopg.Error as exc:
            connection.rollback()
            return build_result(
                request_id,
                "failed",
                errors_count=1,
                error_code="postgres_checkpoint_read_failed",
                error_detail=str(exc),
            )
        except (OSError, ValueError) as exc:
            connection.rollback()
            return build_result(
                request_id,
                "failed",
                errors_count=1,
                error_code="source_invalid",
                error_detail=str(exc),
            )

        events = batch.events
        try:
            if existing_run is None:
                run_id = create_pipeline_run(
                    connection,
                    len(events),
                    request_id=request_id,
                    triggered_by=triggered_by,
                    source_key=source,
                    mode=mode,
                    source_offset_start=position.offset,
                    checkpoint_reset_reason=position.reset_reason,
                )
            else:
                run_id = int(existing_run["id"])
                reopen_pipeline_run(
                    connection,
                    run_id=run_id,
                    events_read=len(events),
                    source_offset_start=position.offset,
                    checkpoint_reset_reason=position.reset_reason,
                )
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
        partial_errors = len(batch.invalid_events)
        try:
            if events:
                inserted = insert_events(connection, events, source_mode)
                session_keys = refresh_sessions(connection, events)
                recalculate_scores(connection, session_keys)
                generate_session_alerts(connection, session_keys, run_id)
                dispatch_pending_alerts(connection, TelegramAdapter.from_env())
                enrich_session_ips(connection, IpApiAdapter())
                enrich_download_hashes(connection, VirusTotalAdapter())
                src_ips = {e["src_ip"] for e in events if e.get("src_ip")}
                geo_lookup = build_geo_lookup(connection, src_ips)
                indexed = index_events(
                    elasticsearch_url,
                    elasticsearch_index,
                    events,
                    geo_lookup=geo_lookup,
                )
            generate_scheduled_reports(connection, pipeline_run_id=run_id)
            save_event_errors(
                connection,
                run_id=run_id,
                source_key=source,
                invalid_events=batch.invalid_events,
            )
            if mode == "incremental":
                save_checkpoint(
                    connection,
                    source_key=source,
                    identity=batch.identity,
                    batch=batch,
                    run_id=run_id,
                    reset_reason=position.reset_reason,
                )
            finish_pipeline_run(
                connection,
                run_id,
                inserted,
                indexed,
                "completed_with_errors" if partial_errors else "completed",
                errors=partial_errors,
                source_offset_end=batch.next_offset,
            )
        except Exception as exc:
            connection.rollback()
            if isinstance(exc, psycopg.Error):
                error_code = "postgres_write_failed"
            elif "Elasticsearch" in str(exc):
                error_code = "elasticsearch_failed"
            else:
                error_code = "pipeline_internal_error"
            try:
                finish_pipeline_run(
                    connection,
                    run_id,
                    inserted,
                    indexed,
                    "failed",
                    errors=1,
                    source_offset_end=batch.next_offset,
                    error_code=error_code,
                    error_detail=str(exc),
                )
            except psycopg.Error:
                connection.rollback()

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
                source_offset_start=position.offset,
                source_offset_end=batch.next_offset,
                checkpoint_reset_reason=position.reset_reason,
            )

    return build_result(
        request_id,
        "completed_with_errors" if partial_errors else "completed",
        run_id=run_id,
        events_read=len(events),
        events_inserted=inserted,
        events_indexed=indexed,
        errors_count=partial_errors,
        source_offset_start=position.offset,
        source_offset_end=batch.next_offset,
        checkpoint_reset_reason=position.reset_reason,
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
    if result["status"] in {"completed", "completed_with_errors"}:
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
        "postgres_checkpoint_read_failed": 4,
        "postgres_write_failed": 4,
        "elasticsearch_failed": 5,
    }.get(str(result["error_code"]), 10)


if __name__ == "__main__":
    raise SystemExit(main())
