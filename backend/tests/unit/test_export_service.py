from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.export_service import ExportFailed, ExportService, _csv_bytes
from app.domain.analytics import EventFilters
from app.domain.identity import Role, UserIdentity


class FailingExportRepository:
    def __init__(self) -> None:
        self.export_id = uuid4()
        self.failure: tuple[UUID, str] | None = None

    async def start_export(self, **_: object) -> UUID:
        return self.export_id

    async def list_events(self, **_: object):
        raise RuntimeError("database unavailable")

    async def fail_export(
        self,
        *,
        export_id: UUID,
        error_code: str,
    ) -> None:
        self.failure = (export_id, error_code)


def test_csv_uses_bom_unicode_and_formula_protection() -> None:
    content = _csv_bytes(
        ("name", "value"),
        (("País", "=2+2"), ("usuario", "@command")),
    )
    assert content.startswith(b"\xef\xbb\xbf")
    decoded = content.decode("utf-8-sig")
    assert "País" in decoded
    assert "'=2+2" in decoded
    assert "'@command" in decoded
    assert "\r\n" in decoded


@pytest.mark.asyncio
async def test_failed_export_is_recorded() -> None:
    repository = FailingExportRepository()
    service = ExportService(repository, rules_version="1.0.0")
    actor = UserIdentity(
        id=uuid4(),
        username="viewer",
        password_hash="unused",
        role=Role.VIEWER,
        is_active=True,
    )

    with pytest.raises(ExportFailed):
        await service.events_csv(
            actor=actor,
            page=1,
            page_size=100,
            filters=EventFilters(
                from_at=datetime(2026, 6, 25, tzinfo=timezone.utc)
            ),
        )

    assert repository.failure == (repository.export_id, "RuntimeError")
