from __future__ import annotations

from typing import Any

from .adapter import VirusTotalAdapter
from .cache import VT_TTL_DAYS, store_vt

_LOAD_UNCACHED_HASHES_SQL = """
SELECT DISTINCT shasum
FROM eventos
WHERE eventid = 'cowrie.session.file.download'
  AND shasum IS NOT NULL
  AND shasum NOT IN (
      SELECT sha256 FROM vt_hash_cache WHERE expires_at > NOW()
  )
LIMIT 10
"""


def enrich_download_hashes(
    connection: Any,
    adapter: VirusTotalAdapter,
    *,
    ttl_days: int = VT_TTL_DAYS,
) -> int:
    with connection.cursor() as cur:
        cur.execute(_LOAD_UNCACHED_HASHES_SQL)
        hashes = [row[0] for row in cur.fetchall()]

    enriched = 0
    for sha256 in hashes:
        result = adapter.query(sha256)
        if result.error != "no_api_key":
            store_vt(connection, result, ttl_days=ttl_days)
        if result.error is None:
            enriched += 1
    return enriched
