from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
from io import StringIO
from typing import Iterable

from app.domain.analytics import (
    EventFilters,
    EventListItem,
    ExportArtifact,
    SessionFilters,
    SessionListItem,
)
from app.domain.identity import UserIdentity
from app.domain.ports.analytics_repository import AnalyticsRepository


class ExportFailed(Exception):
    pass


def _safe_cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _csv_bytes(headers: tuple[str, ...], rows: Iterable[tuple[object, ...]]) -> bytes:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(headers)
    writer.writerows(tuple(_safe_cell(value) for value in row) for row in rows)
    return buffer.getvalue().encode("utf-8-sig")


def _filter_metadata(filters: object) -> dict[str, object]:
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in asdict(filters).items()
        if value is not None
    }


class ExportService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        *,
        rules_version: str,
    ) -> None:
        self._repository = repository
        self._rules_version = rules_version

    async def sessions_csv(
        self,
        *,
        actor: UserIdentity,
        page: int,
        page_size: int,
        filters: SessionFilters,
    ) -> ExportArtifact:
        export_id = await self._repository.start_export(
            user_id=actor.id,
            resource="sessions",
            page=page,
            page_size=page_size,
            filters=_filter_metadata(filters),
            encoding="utf-8-sig",
        )
        try:
            result = await self._repository.list_sessions(
                page=page,
                page_size=page_size,
                rules_version=self._rules_version,
                filters=filters,
            )
            filename = self._filename("sessions")
            content = _csv_bytes(
                (
                    "session_key",
                    "session_id",
                    "sensor",
                    "src_ip",
                    "country",
                    "username",
                    "first_event_at",
                    "last_event_at",
                    "lifecycle_status",
                    "event_count",
                    "command_count",
                    "download_count",
                    "risk_score",
                    "risk_level",
                    "reviewed",
                    "reviewed_at",
                    "reviewed_by_username",
                ),
                (self._session_row(item) for item in result.items),
            )
            await self._repository.complete_export(
                export_id=export_id,
                row_count=len(result.items),
                total_rows=result.total,
                filename=filename,
            )
            return ExportArtifact(
                export_id=export_id,
                filename=filename,
                content=content,
                row_count=len(result.items),
                total_rows=result.total,
                page=page,
                page_size=page_size,
            )
        except Exception as exc:
            await self._repository.fail_export(
                export_id=export_id,
                error_code=type(exc).__name__,
            )
            raise ExportFailed from exc

    async def events_csv(
        self,
        *,
        actor: UserIdentity,
        page: int,
        page_size: int,
        filters: EventFilters,
    ) -> ExportArtifact:
        export_id = await self._repository.start_export(
            user_id=actor.id,
            resource="events",
            page=page,
            page_size=page_size,
            filters=_filter_metadata(filters),
            encoding="utf-8-sig",
        )
        try:
            result = await self._repository.list_events(
                page=page,
                page_size=page_size,
                filters=filters,
            )
            filename = self._filename("events")
            content = _csv_bytes(
                (
                    "id",
                    "timestamp",
                    "event_type",
                    "session_id",
                    "sensor",
                    "src_ip",
                    "src_port",
                    "country",
                    "username",
                    "command",
                    "url",
                    "sha256",
                ),
                (self._event_row(item) for item in result.items),
            )
            await self._repository.complete_export(
                export_id=export_id,
                row_count=len(result.items),
                total_rows=result.total,
                filename=filename,
            )
            return ExportArtifact(
                export_id=export_id,
                filename=filename,
                content=content,
                row_count=len(result.items),
                total_rows=result.total,
                page=page,
                page_size=page_size,
            )
        except Exception as exc:
            await self._repository.fail_export(
                export_id=export_id,
                error_code=type(exc).__name__,
            )
            raise ExportFailed from exc

    @staticmethod
    def _filename(resource: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"oscorp-{resource}-{stamp}.csv"

    @staticmethod
    def _session_row(item: SessionListItem) -> tuple[object, ...]:
        return (
            item.session_key,
            item.session_id,
            item.sensor,
            item.src_ip,
            item.country,
            item.username,
            item.first_event_at,
            item.last_event_at,
            item.lifecycle_status,
            item.event_count,
            item.command_count,
            item.download_count,
            item.risk_score,
            item.risk_level,
            item.reviewed,
            item.reviewed_at,
            item.reviewed_by_username,
        )

    @staticmethod
    def _event_row(item: EventListItem) -> tuple[object, ...]:
        return (
            item.id,
            item.timestamp,
            item.event_type,
            item.session_id,
            item.sensor,
            item.src_ip,
            item.src_port,
            item.country,
            item.username,
            item.command,
            item.url,
            item.sha256,
        )
