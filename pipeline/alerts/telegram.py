from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from urllib.error import HTTPError, URLError

_TRIGGER_TYPE_LABELS: dict[str, str] = {
    "high_risk": "ALTO RIESGO",
    "successful_login": "LOGIN EXITOSO",
    "file_download": "DESCARGA DE ARCHIVO",
}

_RISK_EMOJI: dict[str, str] = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🟠",
    "critical": "🔴",
}


def _http_error_detail(exc: HTTPError) -> str:
    detail = exc.reason
    try:
        body = exc.read().decode("utf-8", errors="replace")
        payload = json.loads(body)
        if isinstance(payload, dict) and payload.get("description"):
            detail = str(payload["description"])
    except Exception:  # noqa: BLE001
        pass
    return f"http_{exc.code}: {detail}"


def format_alert_message(
    *,
    trigger: str,
    session_key: str,
    risk_level: str | None,
    risk_score: int | None,
    event_timestamp: str | None,
    src_ip: str | None = None,
    username: str | None = None,
    duration_seconds: int | None = None,
    download_count: int | None = None,
) -> str:
    emoji = _RISK_EMOJI.get(risk_level or "", "⚪")
    risk_str = risk_level.upper() if risk_level else "N/A"
    score_part = f" · {risk_score}" if risk_score is not None else ""
    tipo = _TRIGGER_TYPE_LABELS.get(trigger, trigger.upper())

    lines = [
        "🚨 ALERTA DE INTRUSIÓN 🚨",
        "",
        f"{emoji} Riesgo: {risk_str}{score_part}",
        f"📡 Tipo: {tipo}",
        "",
        f"🖥️ Sesión: {session_key}",
        f"🌐 IP Atacante: {src_ip or 'N/A'}",
        f"👤 Usuario: {username or 'N/A'}",
        f"⏱️ Duración: {duration_seconds if duration_seconds is not None else 'N/A'}s",
        f"📥 Descargas: {download_count if download_count is not None else 'N/A'}",
    ]
    if event_timestamp is not None:
        lines += ["", f"🕐 {event_timestamp}"]
    lines += ["", "🤖 OSCORP ThreatLab · Detección automática"]
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class TelegramAdapter:
    bot_token: str
    chat_id: str

    @classmethod
    def from_env(cls) -> "TelegramAdapter | None":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not (token and chat_id):
            return None
        return cls(bot_token=token, chat_id=chat_id)

    def send(self, message: str) -> tuple[bool, str | None]:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps(
            {"chat_id": self.chat_id, "text": message},
            ensure_ascii=False,
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return True, None
        except HTTPError as exc:
            return False, _http_error_detail(exc)
        except URLError as exc:
            return False, f"url_error: {exc.reason}"
        except Exception as exc:  # noqa: BLE001
            return False, f"unexpected: {exc}"
