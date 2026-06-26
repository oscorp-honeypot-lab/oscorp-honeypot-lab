from __future__ import annotations

import ipaddress
import json
import urllib.request
from dataclasses import dataclass
from urllib.error import HTTPError, URLError

_FIELDS = "status,message,country,countryCode,city,isp,as,lat,lon"


def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return True


@dataclass(frozen=True, slots=True)
class GeoResult:
    ip: str
    country: str | None
    country_code: str | None
    city: str | None
    isp: str | None
    asn: str | None
    latitude: float | None
    longitude: float | None
    error: str | None


def _empty(ip: str, error: str) -> GeoResult:
    return GeoResult(
        ip=ip, country=None, country_code=None, city=None,
        isp=None, asn=None, latitude=None, longitude=None,
        error=error,
    )


class IpApiAdapter:
    def query(self, ip: str) -> GeoResult:
        if _is_private(ip):
            return _empty(ip, "private_range")
        url = f"http://ip-api.com/json/{ip}?fields={_FIELDS}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read())
            if data.get("status") == "success":
                return GeoResult(
                    ip=ip,
                    country=data.get("country"),
                    country_code=data.get("countryCode"),
                    city=data.get("city"),
                    isp=data.get("isp"),
                    asn=data.get("as"),
                    latitude=float(data["lat"]) if data.get("lat") is not None else None,
                    longitude=float(data["lon"]) if data.get("lon") is not None else None,
                    error=None,
                )
            return _empty(ip, f"api_fail:{data.get('message', '')}")
        except HTTPError as exc:
            if exc.code == 429:
                return _empty(ip, "rate_limited")
            return _empty(ip, f"http_{exc.code}:{exc.reason}")
        except URLError as exc:
            return _empty(ip, f"url_error:{exc.reason}")
        except Exception as exc:  # noqa: BLE001
            return _empty(ip, f"unexpected:{exc}")
