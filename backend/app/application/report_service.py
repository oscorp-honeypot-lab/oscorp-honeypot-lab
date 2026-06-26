from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from io import StringIO
import json
from typing import Any, Protocol

from app.domain.analytics import ReportArtifact, ReportDelivery, ReportRun
from app.domain.identity import UserIdentity
from app.domain.ports.analytics_repository import AnalyticsRepository


class ReportNotFound(Exception):
    pass


class ReportFormatUnsupported(Exception):
    pass


class ReportDeliveryFailed(Exception):
    pass


class TelegramSender(Protocol):
    def send(self, message: str) -> tuple[bool, str | None]: ...


@dataclass(frozen=True, slots=True)
class ReportFormat:
    extension: str
    media_type: str
    content: bytes


def _safe_cell(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _fmt(value: object) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _section_rows(title: str, rows: list[dict[str, object]]) -> str:
    if not rows:
        return f"<section><h2>{escape(title)}</h2><p>Sin datos.</p></section>"
    headers = tuple(rows[0].keys())
    head = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
    body = "".join(
        "<tr>"
        + "".join(f"<td>{escape(_fmt(row.get(header)))}</td>" for header in headers)
        + "</tr>"
        for row in rows
    )
    return (
        f"<section><h2>{escape(title)}</h2>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        "</section>"
    )


def _dataset_rows(dataset: dict[str, Any]) -> dict[str, list[dict[str, object]]]:
    totals = dataset.get("totals", {})
    downloads = dataset.get("downloads", {})
    critical = dataset.get("critical_sessions", {})
    mttd = dataset.get("mttd", {})
    failed = dataset.get("failed_alerts", {})
    return {
        "totals": [dict(totals)] if isinstance(totals, dict) else [],
        "top_source_ips": list(dataset.get("top_source_ips", [])),
        "top_countries": list(dataset.get("top_countries", [])),
        "top_credentials": list(dataset.get("top_credentials", [])),
        "top_commands": list(dataset.get("top_commands", [])),
        "downloads": [
            {
                "downloads": downloads.get("downloads"),
                "unique_hashes": downloads.get("unique_hashes"),
            }
        ] if isinstance(downloads, dict) else [],
        "top_files": list(downloads.get("top_files", [])) if isinstance(downloads, dict) else [],
        "malicious_hashes": list(dataset.get("malicious_hashes", [])),
        "critical_sessions": [
            {"total": critical.get("total")}
        ] if isinstance(critical, dict) else [],
        "critical_top_sessions": (
            list(critical.get("top_sessions", [])) if isinstance(critical, dict) else []
        ),
        "mttd": [dict(mttd)] if isinstance(mttd, dict) else [],
        "failed_alerts": [
            {
                "total_failed": failed.get("total_failed"),
                "affected_sessions": failed.get("affected_sessions"),
            }
        ] if isinstance(failed, dict) else [],
        "failed_alerts_by_error": (
            list(failed.get("by_error_code", [])) if isinstance(failed, dict) else []
        ),
    }


def _html_report(report: ReportRun) -> bytes:
    dataset = report.dataset
    title = f"OSCORP ThreatLab - Reporte {report.period_type}"
    rows = _dataset_rows(dataset)
    sections = "\n".join(
        _section_rows(label.replace("_", " ").title(), value)
        for label, value in rows.items()
    )
    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172026; }}
    h1 {{ margin-bottom: 4px; }}
    h2 {{ margin-top: 28px; border-bottom: 1px solid #ccd3d8; padding-bottom: 6px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
    th, td {{ border: 1px solid #d8dee3; padding: 7px 9px; text-align: left; }}
    th {{ background: #eef2f4; }}
    .meta {{ color: #52616b; margin-bottom: 24px; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p class="meta">
    Periodo: {escape(report.period_start.isoformat())}
    a {escape(report.period_end.isoformat())}
  </p>
  {sections}
</body>
</html>
"""
    return html.encode("utf-8")


def _csv_report(report: ReportRun) -> bytes:
    rows = _dataset_rows(report.dataset)
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(("section", "field", "value"))
    writer.writerow(("meta", "report_id", str(report.id)))
    writer.writerow(("meta", "period_type", report.period_type))
    writer.writerow(("meta", "period_start", report.period_start.isoformat()))
    writer.writerow(("meta", "period_end", report.period_end.isoformat()))
    for section, items in rows.items():
        for index, item in enumerate(items, start=1):
            for field, value in item.items():
                writer.writerow((section, f"{index}.{field}", _safe_cell(value)))
    return buffer.getvalue().encode("utf-8-sig")


def _format_report(report: ReportRun, format: str) -> ReportFormat:
    if format == "html":
        return ReportFormat(
            extension="html",
            media_type="text/html; charset=utf-8",
            content=_html_report(report),
        )
    if format == "csv":
        return ReportFormat(
            extension="csv",
            media_type="text/csv; charset=utf-8",
            content=_csv_report(report),
        )
    raise ReportFormatUnsupported(format)


def _filename(report: ReportRun, extension: str) -> str:
    stamp = report.period_end.astimezone(timezone.utc).strftime("%Y%m%d")
    return f"oscorp-report-{report.period_type}-{stamp}.{extension}"


def _telegram_summary(report: ReportRun) -> str:
    totals = report.dataset.get("totals", {})
    failed = report.dataset.get("failed_alerts", {})
    mttd = report.dataset.get("mttd", {})
    if not isinstance(totals, dict):
        totals = {}
    if not isinstance(failed, dict):
        failed = {}
    if not isinstance(mttd, dict):
        mttd = {}
    payload = {
        "period_type": report.period_type,
        "period_start": report.period_start.isoformat(),
        "period_end": report.period_end.isoformat(),
        "events": totals.get("events", 0),
        "sessions": totals.get("sessions", 0),
        "unique_source_ips": totals.get("unique_source_ips", 0),
        "critical_sessions": report.dataset.get("critical_sessions", {}).get("total", 0)
        if isinstance(report.dataset.get("critical_sessions"), dict)
        else 0,
        "mttd_avg_seconds": mttd.get("avg_seconds"),
        "failed_alerts": failed.get("total_failed", 0),
    }
    return "OSCORP ThreatLab report\n" + json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )


class ReportService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        telegram_sender: TelegramSender | None = None,
    ) -> None:
        self._repository = repository
        self._telegram_sender = telegram_sender

    async def latest(self, *, period_type: str) -> ReportRun:
        report = await self._repository.get_latest_report(period_type=period_type)
        if report is None:
            raise ReportNotFound(period_type)
        return report

    async def download_latest(
        self,
        *,
        actor: UserIdentity,
        period_type: str,
        format: str,
    ) -> ReportArtifact:
        report = await self.latest(period_type=period_type)
        delivery_id = await self._repository.start_report_delivery(
            report_id=report.id,
            user_id=actor.id,
            channel="download",
            format=format,
        )
        try:
            rendered = _format_report(report, format)
            filename = _filename(report, rendered.extension)
            await self._repository.finish_report_delivery(
                delivery_id=delivery_id,
                status="completed",
                filename=filename,
            )
            return ReportArtifact(
                delivery_id=delivery_id,
                report_id=report.id,
                period_type=report.period_type,
                filename=filename,
                media_type=rendered.media_type,
                content=rendered.content,
            )
        except Exception as exc:
            await self._repository.finish_report_delivery(
                delivery_id=delivery_id,
                status="failed",
                error_code=type(exc).__name__,
                error_detail=str(exc),
            )
            raise

    async def send_latest_telegram(
        self,
        *,
        actor: UserIdentity,
        period_type: str,
        format: str,
    ) -> ReportDelivery:
        report = await self.latest(period_type=period_type)
        delivery_id = await self._repository.start_report_delivery(
            report_id=report.id,
            user_id=actor.id,
            channel="telegram",
            format=format,
        )
        filename: str | None = None
        try:
            rendered = _format_report(report, format)
            filename = _filename(report, rendered.extension)
            if self._telegram_sender is None:
                await self._repository.finish_report_delivery(
                    delivery_id=delivery_id,
                    status="skipped",
                    filename=filename,
                    error_code="telegram_not_configured",
                )
                return ReportDelivery(
                    id=delivery_id,
                    report_id=report.id,
                    channel="telegram",
                    format=format,
                    status="skipped",
                    filename=filename,
                    error_code="telegram_not_configured",
                )
            ok, error = self._telegram_sender.send(_telegram_summary(report))
            status = "completed" if ok else "failed"
            await self._repository.finish_report_delivery(
                delivery_id=delivery_id,
                status=status,
                filename=filename,
                error_code=error,
            )
            if not ok:
                raise ReportDeliveryFailed(error or "telegram_failed")
            return ReportDelivery(
                id=delivery_id,
                report_id=report.id,
                channel="telegram",
                format=format,
                status=status,
                filename=filename,
                error_code=error,
            )
        except ReportDeliveryFailed:
            raise
        except Exception as exc:
            await self._repository.finish_report_delivery(
                delivery_id=delivery_id,
                status="failed",
                filename=filename,
                error_code=type(exc).__name__,
                error_detail=str(exc),
            )
            raise
