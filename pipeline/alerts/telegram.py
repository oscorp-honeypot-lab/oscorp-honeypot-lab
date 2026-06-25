from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from urllib.error import HTTPError, URLError


_TRIGGER_LABELS: dict[str, str] = {
    "high_risk": "Sesión de alto riesgo detectada",
    "successful_login": "Login exitoso en honeypot",
    "file_download": "Descarga de archivo en honeypot",
}

_RISK_EMOJI: dict[str, str] = {
    "low": "🟢",
    "medium": "🟡",
    "high": "🟠",
    "critical": "🔴",
}


def format_alert_message(
    *,
    trigger: str,
    session_key: str,
    risk_level: str | None,
    risk_score: int | None,
    event_timestamp: str | None,
) -> str:
    label = _TRIGGER_LABELS.get(trigger, trigger)
    lines = [
        "<b>OSCORP ThreatLab — Alerta</b>",
        label,
        f"Sesión: <code>{session_key}</code>",
    ]
    if risk_level is not None:
        emoji = _RISK_EMOJI.get(risk_level, "⚪")
        score_part = f" · {risk_score}" if risk_score is not None else ""
        lines.append(f"Riesgo: {emoji} {risk_level}{score_part}")
    if event_timestamp is not None:
        lines.append(f"Evento: {event_timestamp}")
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
            {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"},
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
            return False, f"http_{exc.code}: {exc.reason}"
        except URLError as exc:
            return False, f"url_error: {exc.reason}"
        except Exception as exc:  # noqa: BLE001
            return False, f"unexpected: {exc}"
