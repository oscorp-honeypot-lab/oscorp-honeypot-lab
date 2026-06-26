from __future__ import annotations

from typing import Any

from .adapter import IpApiAdapter
from .cache import store_geo

GEO_TTL_DAYS: int = 7

_LOAD_UNCACHED_IPS_SQL = """
SELECT DISTINCT src_ip
FROM sessions
WHERE src_ip IS NOT NULL
  AND src_ip NOT IN (
      SELECT ip FROM ip_geo_cache WHERE expires_at > NOW()
  )
LIMIT 30
"""


def enrich_session_ips(
    connection: Any,
    adapter: IpApiAdapter,
    *,
    ttl_days: int = GEO_TTL_DAYS,
) -> int:
    with connection.cursor() as cur:
        cur.execute(_LOAD_UNCACHED_IPS_SQL)
        ips = [row[0] for row in cur.fetchall()]

    enriched = 0
    for ip in ips:
        result = adapter.query(ip)
        store_geo(connection, result, ttl_days=ttl_days)
        if result.error is None:
            enriched += 1
    return enriched
