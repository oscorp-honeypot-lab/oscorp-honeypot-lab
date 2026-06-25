from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.application.analytics_service import AnalyticsService
from app.domain.analytics import AlertItem, Page


BASE_TS = datetime(2026, 6, 25, 18, 0, tzinfo=timezone.utc)

ALERT_ID = uuid4()


def _alert(
    *,
    id: UUID = ALERT_ID,
    session_key: str = "sensor:abc123",
    trigger: str = "high_risk",
    channel: str = "telegram",
    status: str = "pending",
    risk_level: str | None = "high",
    risk_score: int | None = 75,
    event_timestamp: datetime | None = BASE_TS,
    triggered_at: datetime = BASE_TS,
    sent_at: datetime | None = None,
    mttd_seconds: float | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
) -> AlertItem:
    return AlertItem(
        id=id,
        session_key=session_key,
        trigger=trigger,
        channel=channel,
        status=status,
        risk_level=risk_level,
        risk_score=risk_score,
        event_timestamp=event_timestamp,
        triggered_at=triggered_at,
        sent_at=sent_at,
        mttd_seconds=mttd_seconds,
        error_code=error_code,
        error_detail=error_detail,
    )


class StubAlertRepository:
    def __init__(self, alerts: tuple[AlertItem, ...] = ()) -> None:
        self._alerts = alerts
        self.last_call: dict = {}

    async def list_alerts(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        session_key: str | None = None,
    ) -> Page[AlertItem]:
        self.last_call = {
            "page": page,
            "page_size": page_size,
            "status": status,
            "session_key": session_key,
        }
        filtered = self._alerts
        if status is not None:
            filtered = tuple(a for a in filtered if a.status == status)
        if session_key is not None:
            filtered = tuple(a for a in filtered if a.session_key == session_key)
        return Page(items=filtered, page=page, page_size=page_size, total=len(filtered))

    def __getattr__(self, name: str):
        raise AttributeError(f"StubAlertRepository has no method '{name}'")


def _service(alerts: tuple[AlertItem, ...] = ()) -> AnalyticsService:
    return AnalyticsService(
        repository=StubAlertRepository(alerts),  # type: ignore[arg-type]
        rules_version="1.0.0",
    )


@pytest.mark.anyio
async def test_list_alerts_returns_empty_page_when_no_alerts() -> None:
    service = _service()
    page = await service.list_alerts(page=1, page_size=50)
    assert page.total == 0
    assert page.items == ()


@pytest.mark.anyio
async def test_list_alerts_returns_alerts() -> None:
    alert = _alert()
    service = _service((alert,))
    page = await service.list_alerts(page=1, page_size=50)
    assert page.total == 1
    assert page.items[0].trigger == "high_risk"
    assert page.items[0].channel == "telegram"
    assert page.items[0].status == "pending"


@pytest.mark.anyio
async def test_list_alerts_filters_by_status() -> None:
    pending = _alert(status="pending")
    sent = _alert(id=uuid4(), status="sent")
    service = _service((pending, sent))
    page = await service.list_alerts(page=1, page_size=50, status="pending")
    assert page.total == 1
    assert page.items[0].status == "pending"


@pytest.mark.anyio
async def test_list_alerts_filters_by_session_key() -> None:
    alert_a = _alert(session_key="sensor:aaa")
    alert_b = _alert(id=uuid4(), session_key="sensor:bbb")
    service = _service((alert_a, alert_b))
    page = await service.list_alerts(page=1, page_size=50, session_key="sensor:aaa")
    assert page.total == 1
    assert page.items[0].session_key == "sensor:aaa"


@pytest.mark.anyio
async def test_list_alerts_forwards_pagination_to_repository() -> None:
    repo = StubAlertRepository()
    service = AnalyticsService(
        repository=repo,  # type: ignore[arg-type]
        rules_version="1.0.0",
    )
    await service.list_alerts(page=3, page_size=10)
    assert repo.last_call["page"] == 3
    assert repo.last_call["page_size"] == 10
