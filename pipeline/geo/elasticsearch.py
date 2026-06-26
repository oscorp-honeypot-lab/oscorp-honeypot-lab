from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import psycopg

_GEO_LOOKUP_SQL = """
SELECT ip, latitude, longitude
FROM ip_geo_cache
WHERE ip = ANY(%(ips)s)
  AND expires_at > NOW()
  AND error IS NULL
  AND latitude IS NOT NULL
  AND longitude IS NOT NULL
"""


def geo_location_for_ip(
    lat: float | None, lon: float | None
) -> dict[str, float] | None:
    if lat is None or lon is None:
        return None
    return {"lat": float(lat), "lon": float(lon)}


def build_geo_lookup(
    connection: Any,
    src_ips: set[str],
) -> dict[str, dict[str, float]]:
    if not src_ips:
        return {}
    with connection.cursor() as cur:
        cur.execute(_GEO_LOOKUP_SQL, {"ips": list(src_ips)})
        rows = cur.fetchall()
    result: dict[str, dict[str, float]] = {}
    for ip, lat, lon in rows:
        loc = geo_location_for_ip(lat, lon)
        if loc is not None:
            result[str(ip)] = loc
    return result
