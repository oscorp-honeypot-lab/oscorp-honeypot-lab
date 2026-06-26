from __future__ import annotations

from typing import Any

from .adapter import VtResult

_GET_SQL = """
SELECT malicious, suspicious, undetected, harmless, timeout,
       last_analysis_date, reputation, error
FROM vt_hash_cache
WHERE sha256 = %(sha256)s AND expires_at > NOW()
"""

_UPSERT_SQL = """
INSERT INTO vt_hash_cache
    (sha256, malicious, suspicious, undetected, harmless, timeout,
     last_analysis_date, reputation, error, expires_at)
VALUES
    (%(sha256)s, %(malicious)s, %(suspicious)s, %(undetected)s, %(harmless)s,
     %(timeout)s, %(last_analysis_date)s, %(reputation)s, %(error)s,
     NOW() + %(ttl_days)s * INTERVAL '1 day')
ON CONFLICT (sha256) DO UPDATE SET
    malicious           = EXCLUDED.malicious,
    suspicious          = EXCLUDED.suspicious,
    undetected          = EXCLUDED.undetected,
    harmless            = EXCLUDED.harmless,
    timeout             = EXCLUDED.timeout,
    last_analysis_date  = EXCLUDED.last_analysis_date,
    reputation          = EXCLUDED.reputation,
    error               = EXCLUDED.error,
    queried_at          = NOW(),
    expires_at          = EXCLUDED.expires_at
"""

VT_TTL_DAYS: int = 30


def get_cached_vt(connection: Any, sha256: str) -> VtResult | None:
    with connection.cursor() as cur:
        cur.execute(_GET_SQL, {"sha256": sha256})
        row = cur.fetchone()
    if row is None:
        return None
    malicious, suspicious, undetected, harmless, timeout, lad, reputation, error = row
    return VtResult(
        sha256=sha256,
        malicious=int(malicious) if malicious is not None else None,
        suspicious=int(suspicious) if suspicious is not None else None,
        undetected=int(undetected) if undetected is not None else None,
        harmless=int(harmless) if harmless is not None else None,
        timeout=int(timeout) if timeout is not None else None,
        last_analysis_date=int(lad) if lad is not None else None,
        reputation=int(reputation) if reputation is not None else None,
        error=str(error) if error is not None else None,
    )


def store_vt(connection: Any, result: VtResult, *, ttl_days: int = VT_TTL_DAYS) -> None:
    with connection.cursor() as cur:
        cur.execute(
            _UPSERT_SQL,
            {
                "sha256": result.sha256,
                "malicious": result.malicious,
                "suspicious": result.suspicious,
                "undetected": result.undetected,
                "harmless": result.harmless,
                "timeout": result.timeout,
                "last_analysis_date": result.last_analysis_date,
                "reputation": result.reputation,
                "error": result.error,
                "ttl_days": ttl_days,
            },
        )
    connection.commit()
