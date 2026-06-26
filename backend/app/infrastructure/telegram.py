from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from urllib.error import HTTPError, URLError


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


@dataclass(frozen=True, slots=True)
class TelegramAdapter:
    bot_token: str
    chat_id: str

    @classmethod
    def from_settings(
        cls,
        *,
        bot_token: str,
        chat_id: str,
    ) -> "TelegramAdapter | None":
        token = bot_token.strip()
        chat = chat_id.strip()
        if not (token and chat):
            return None
        return cls(bot_token=token, chat_id=chat)

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
