from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from io import StringIO
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


_SECTION_H2 = (
    'font-size:0.75rem;text-transform:uppercase;letter-spacing:.1em;'
    'color:#087e8b;font-weight:700;margin-bottom:12px;'
)


_TABLE_MAX_HEIGHT = "280px"


def _table_block(
    title: str,
    rows: list[dict[str, object]],
    *,
    compact: bool = False,
) -> str:
    label = escape(title)
    if not rows:
        return (
            f'<h2 style="{_SECTION_H2}">{label}</h2>'
            f'<p style="color:#68747a;font-size:0.85rem;font-style:italic;">Sin datos disponibles.</p>'
        )
    table_layout = "table-layout:fixed;" if compact else ""
    wrap_style = "overflow-wrap:break-word;" if compact else "white-space:nowrap;"
    th_padding = "6px 8px" if compact else "9px 14px"
    th_font_size = "0.62rem" if compact else "0.72rem"
    td_padding = "6px 8px" if compact else "8px 14px"
    td_font_size = "0.78rem" if compact else "0.86rem"
    headers = tuple(rows[0].keys())
    head_cells = "".join(
        f'<th style="padding:{th_padding};text-align:left;font-size:{th_font_size};text-transform:uppercase;'
        f'letter-spacing:.07em;background:#202427;color:#7bd3db;font-weight:700;'
        f'{wrap_style}position:sticky;top:0;">'
        f'{escape(str(h).replace("_", " "))}</th>'
        for h in headers
    )
    body_rows = ""
    for i, row in enumerate(rows):
        bg = "#f8fafb" if i % 2 == 0 else "#ffffff"
        cells = "".join(
            f'<td style="padding:{td_padding};border-bottom:1px solid #dce1e4;'
            f'color:#172026;font-size:{td_font_size};{"overflow-wrap:break-word;" if compact else ""}">'
            f'{escape(_fmt(row.get(h)))}</td>'
            for h in headers
        )
        body_rows += f'<tr style="background:{bg};">{cells}</tr>'
    return (
        f'<h2 style="{_SECTION_H2}">{label}</h2>'
        f'<div style="border:1px solid #dce1e4;border-radius:8px;'
        f'max-height:{_TABLE_MAX_HEIGHT};overflow-y:auto;overflow-x:hidden;">'
        f'<table style="border-collapse:collapse;width:100%;{table_layout}">'
        f'<thead><tr>{head_cells}</tr></thead>'
        f'<tbody>{body_rows}</tbody>'
        f'</table></div>'
    )


def _section_rows(title: str, rows: list[dict[str, object]]) -> str:
    return f'<section style="margin-bottom:32px;">{_table_block(title, rows)}</section>'


_SIDE_BY_SIDE_LABELS = ("top_countries", "top_credentials", "top_commands")


def _secondary_tables_grid(rows: dict[str, list[dict[str, object]]]) -> str:
    columns = "".join(
        f'<div>{_table_block(label.replace("_", " ").title(), rows.get(label, []), compact=True)}</div>'
        for label in _SIDE_BY_SIDE_LABELS
    )
    return (
        '<section style="margin-bottom:32px;">'
        '<div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:20px;align-items:start;">'
        f"{columns}"
        "</div></section>"
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


_TOTALS_STYLE: dict[str, tuple[str, str, str]] = {
    "events": ("Eventos totales", "#087e8b", "#e6f4f5"),
    "sessions": ("Sesiones SSH", "#087e8b", "#e6f4f5"),
    "unique_source_ips": ("IPs únicas", "#9c3f00", "#ffe2c7"),
    "successful_login_sessions": ("Logins exitosos", "#9d1c24", "#fde1e3"),
    "download_sessions": ("Descargas", "#6c4f00", "#fff2c2"),
}


def _totals_cards(rows: list[dict[str, object]]) -> str:
    if not rows:
        return ""
    totals = rows[0]
    cards: list[str] = []
    for key, value in totals.items():
        label, color, bg = _TOTALS_STYLE.get(
            key, (key.replace("_", " ").title(), "#087e8b", "#e6f4f5")
        )
        cards.append(
            f'<div style="background:{bg};border-left:4px solid {color};border-radius:8px;'
            f'padding:18px 24px;min-width:140px;flex:1;">'
            f'<div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:.07em;'
            f'color:{color};font-weight:700;margin-bottom:8px;">{escape(label)}</div>'
            f'<div style="font-size:2rem;font-weight:800;color:{color};">{escape(_fmt(value))}</div>'
            f'</div>'
        )
    return (
        '<section style="margin-bottom:32px;">'
        f'<h2 style="{_SECTION_H2}">RESUMEN OPERATIVO</h2>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(140px, 1fr));'
        f'gap:12px;">{"".join(cards)}</div>'
        '</section>'
    )


def _html_report(report: ReportRun) -> bytes:
    dataset = report.dataset
    title = f"OSCORP ThreatLab - Reporte {report.period_type}"
    rows = _dataset_rows(dataset)
    generated = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    period_str = (
        f"{report.period_start.strftime('%Y-%m-%d %H:%M')} "
        f"→ {report.period_end.strftime('%Y-%m-%d %H:%M')} UTC"
    )
    totals_html = _totals_cards(rows.get("totals", []))
    section_blocks: list[str] = []
    grid_rendered = False
    for label, value in rows.items():
        if label == "totals":
            continue
        if label in _SIDE_BY_SIDE_LABELS:
            if not grid_rendered:
                section_blocks.append(_secondary_tables_grid(rows))
                grid_rendered = True
            continue
        section_blocks.append(_section_rows(label.replace("_", " ").title(), value))
    sections = "\n".join(section_blocks)
    html = (
        "<!doctype html>\n"
        '<html lang="es">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"  <title>{escape(title)}</title>\n"
        "  <style>\n"
        "    *{box-sizing:border-box;margin:0;padding:0;}\n"
        "    body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;"
        "background:#f4f6f8;color:#172026;}\n"
        "    @media print{body{background:#fff;}}\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        # ── HEADER ──────────────────────────────────────────────────────────
        '  <div style="background:#161a1d;">\n'
        '    <div style="border-bottom:4px solid #f2a900;padding:28px 40px 24px;">\n'
        '      <div style="display:flex;align-items:center;gap:16px;margin-bottom:14px;">\n'
        '        <div style="width:42px;height:42px;border-radius:8px;background:#087e8b;'
        'display:flex;align-items:center;justify-content:center;font-size:1.3rem;'
        'font-weight:900;color:#fff;flex-shrink:0;">O</div>\n'
        '        <div>\n'
        '          <div style="font-size:1.35rem;font-weight:800;color:#ffffff;letter-spacing:.02em;">'
        "OSCORP ThreatLab</div>\n"
        '          <div style="font-size:0.72rem;color:#7bd3db;letter-spacing:.1em;'
        'text-transform:uppercase;margin-top:2px;">SSH Honeypot Platform</div>\n'
        "        </div>\n"
        "      </div>\n"
        '      <div style="margin-top:8px;">\n'
        '        <div style="font-size:0.68rem;text-transform:uppercase;letter-spacing:.1em;'
        f'color:#52616b;margin-bottom:4px;">Reporte de Seguridad · {escape(report.period_type.upper())}</div>\n'
        '        <div style="font-size:1rem;font-weight:600;color:#e8edf0;">'
        f"{escape(period_str)}</div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </div>\n"
        # ── CONTENT ─────────────────────────────────────────────────────────
        '  <div style="max-width:980px;margin:0 auto;padding:36px 24px;">\n'
        f"    {totals_html}\n"
        f"    {sections}\n"
        "  </div>\n"
        # ── FOOTER ──────────────────────────────────────────────────────────
        '  <div style="background:#202427;padding:18px 40px;text-align:center;">\n'
        '    <span style="font-size:0.72rem;color:#52616b;">'
        f"Generado el {escape(generated)} · OSCORP ThreatLab · Uso interno</span>\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )
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
