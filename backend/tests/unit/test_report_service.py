from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.report_service import ReportDeliveryFailed, ReportService
from app.domain.analytics import ReportRun
from app.domain.identity import Role, UserIdentity

REPORT_ID = UUID("10000000-0000-4000-8000-000000000031")
USER_ID = UUID("20000000-0000-4000-8000-000000000031")


def _report() -> ReportRun:
    return ReportRun(
        id=REPORT_ID,
        period_type="daily",
        period_start=datetime(2026, 6, 25, tzinfo=timezone.utc),
        period_end=datetime(2026, 6, 26, tzinfo=timezone.utc),
        status="completed",
        dataset={
            "totals": {"events": 10, "sessions": 2, "unique_source_ips": 1},
            "top_source_ips": [{"src_ip": "203.0.113.10", "event_count": 10}],
            "top_countries": [],
            "top_credentials": [{"username": "root", "password": "admin", "attempts": 2}],
            "top_commands": [{"command": "uname -a", "executions": 1}],
            "downloads": {"downloads": 1, "unique_hashes": 1, "top_files": []},
            "malicious_hashes": [],
            "critical_sessions": {"total": 0, "top_sessions": []},
            "mttd": {"avg_seconds": 12.5, "total_sent": 1, "total_failed": 0},
            "failed_alerts": {"total_failed": 0, "affected_sessions": 0, "by_error_code": []},
        },
    )


def _actor() -> UserIdentity:
    return UserIdentity(
        id=USER_ID,
        username="admin",
        password_hash="hash",
        role=Role.ADMIN,
        is_active=True,
    )


class _Repo:
    def __init__(self) -> None:
        self.finished: list[dict] = []
        self.started: list[dict] = []

    async def get_latest_report(self, *, period_type: str):
        return _report() if period_type == "daily" else None

    async def start_report_delivery(self, **kwargs):
        self.started.append(kwargs)
        return uuid4()

    async def finish_report_delivery(self, **kwargs) -> None:
        self.finished.append(kwargs)


class _Telegram:
    def __init__(self, *, ok: bool, error: str | None = None) -> None:
        self.ok = ok
        self.error = error
        self.messages: list[str] = []

    def send(self, message: str):
        self.messages.append(message)
        return self.ok, self.error


@pytest.mark.asyncio
async def test_download_latest_html_records_completed_delivery() -> None:
    repo = _Repo()
    service = ReportService(repo)
    artifact = await service.download_latest(
        actor=_actor(),
        period_type="daily",
        format="html",
    )
    assert artifact.filename.endswith(".html")
    assert b"OSCORP ThreatLab" in artifact.content
    assert repo.started[0]["channel"] == "download"
    assert repo.finished[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_download_latest_csv_uses_utf8_bom() -> None:
    repo = _Repo()
    service = ReportService(repo)
    artifact = await service.download_latest(
        actor=_actor(),
        period_type="daily",
        format="csv",
    )
    assert artifact.filename.endswith(".csv")
    assert artifact.content.startswith(b"\xef\xbb\xbf")
    assert b"top_credentials" in artifact.content


@pytest.mark.asyncio
async def test_send_latest_telegram_skips_when_not_configured() -> None:
    repo = _Repo()
    service = ReportService(repo)
    delivery = await service.send_latest_telegram(
        actor=_actor(),
        period_type="daily",
        format="html",
    )
    assert delivery.status == "skipped"
    assert delivery.error_code == "telegram_not_configured"
    assert repo.finished[0]["status"] == "skipped"


@pytest.mark.asyncio
async def test_html_report_groups_secondary_tables_in_grid() -> None:
    repo = _Repo()
    service = ReportService(repo)
    artifact = await service.download_latest(
        actor=_actor(),
        period_type="daily",
        format="html",
    )
    html = artifact.content
    assert html.count(b"grid-template-columns:repeat(3, 1fr)") == 1
    assert html.find(b"Top Countries") < html.find(b"Top Credentials")
    assert html.find(b"Top Credentials") < html.find(b"Top Commands")


@pytest.mark.asyncio
async def test_html_report_totals_cards_use_single_row_grid() -> None:
    repo = _Repo()
    service = ReportService(repo)
    artifact = await service.download_latest(
        actor=_actor(),
        period_type="daily",
        format="html",
    )
    assert b"grid-template-columns:repeat(auto-fit, minmax(140px, 1fr))" in artifact.content


@pytest.mark.asyncio
async def test_html_report_tables_have_internal_scroll_limit() -> None:
    repo = _Repo()
    service = ReportService(repo)
    artifact = await service.download_latest(
        actor=_actor(),
        period_type="daily",
        format="html",
    )
    html = artifact.content
    assert b"max-height:280px" in html
    assert b"overflow-y:auto" in html


@pytest.mark.asyncio
async def test_html_report_keeps_all_rows_when_over_scroll_limit() -> None:
    report = _report()
    report.dataset["top_source_ips"] = [
        {"src_ip": f"203.0.113.{i}", "event_count": i} for i in range(10)
    ]

    class _RepoManyRows(_Repo):
        async def get_latest_report(self, *, period_type: str):
            return report if period_type == "daily" else None

    repo = _RepoManyRows()
    service = ReportService(repo)
    artifact = await service.download_latest(
        actor=_actor(),
        period_type="daily",
        format="html",
    )
    html = artifact.content
    for i in range(10):
        assert f"203.0.113.{i}".encode() in html
    assert b"max-height:280px" in html


@pytest.mark.asyncio
async def test_html_report_side_by_side_tables_use_fixed_layout_to_avoid_overflow() -> None:
    repo = _Repo()
    service = ReportService(repo)
    artifact = await service.download_latest(
        actor=_actor(),
        period_type="daily",
        format="html",
    )
    html = artifact.content
    # Top Countries / Top Credentials / Top Commands share a narrow 3-column
    # row, so they need a fixed layout + wrapping to avoid spilling past
    # their column instead of overflowing the page.
    assert html.count(b"table-layout:fixed") == 2  # top_credentials + top_commands (top_countries is empty)
    assert b"overflow-wrap:break-word" in html


@pytest.mark.asyncio
async def test_html_report_full_width_tables_keep_original_auto_layout() -> None:
    repo = _Repo()
    service = ReportService(repo)
    artifact = await service.download_latest(
        actor=_actor(),
        period_type="daily",
        format="html",
    )
    html = artifact.content
    # Full-width tables (Top Source Ips, Downloads, Mttd, ...) have plenty of
    # room at 980px, so they keep their original nowrap/auto-layout look.
    assert b"white-space:nowrap" in html


@pytest.mark.asyncio
async def test_send_latest_telegram_records_failure() -> None:
    repo = _Repo()
    telegram = _Telegram(ok=False, error="http_429: Too Many Requests")
    service = ReportService(repo, telegram)
    with pytest.raises(ReportDeliveryFailed):
        await service.send_latest_telegram(
            actor=_actor(),
            period_type="daily",
            format="html",
        )
    assert "OSCORP ThreatLab report" in telegram.messages[0]
    assert repo.finished[0]["status"] == "failed"
    assert repo.finished[0]["error_code"] == "http_429: Too Many Requests"
