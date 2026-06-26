from __future__ import annotations

from typing import Any

from .adapter import GeoResult

_GET_SQL = """
SELECT country, country_code, city, isp, asn, latitude, longitude, error
FROM ip_geo_cache
WHERE ip = %(ip)s AND expires_at > NOW()
"""

_UPSERT_SQL = """
INSERT INTO ip_geo_cache
    (ip, country, country_code, city, isp, asn, latitude, longitude, error, expires_at)
VALUES
    (%(ip)s, %(country)s, %(country_code)s, %(city)s, %(isp)s, %(asn)s,
     %(latitude)s, %(longitude)s, %(error)s,
     NOW() + %(ttl_days)s * INTERVAL '1 day')
ON CONFLICT (ip) DO UPDATE SET
    country      = EXCLUDED.country,
    country_code = EXCLUDED.country_code,
    city         = EXCLUDED.city,
    isp          = EXCLUDED.isp,
    asn          = EXCLUDED.asn,
    latitude     = EXCLUDED.latitude,
    longitude    = EXCLUDED.longitude,
    error        = EXCLUDED.error,
    queried_at   = NOW(),
    expires_at   = EXCLUDED.expires_at
"""


def get_cached_geo(connection: Any, ip: str) -> GeoResult | None:
    with connection.cursor() as cur:
        cur.execute(_GET_SQL, {"ip": ip})
        row = cur.fetchone()
    if row is None:
        return None
    country, country_code, city, isp, asn, lat, lon, error = row
    return GeoResult(
        ip=ip,
        country=str(country) if country is not None else None,
        country_code=str(country_code) if country_code is not None else None,
        city=str(city) if city is not None else None,
        isp=str(isp) if isp is not None else None,
        asn=str(asn) if asn is not None else None,
        latitude=float(lat) if lat is not None else None,
        longitude=float(lon) if lon is not None else None,
        error=str(error) if error is not None else None,
    )


def store_geo(connection: Any, result: GeoResult, *, ttl_days: int = 7) -> None:
    with connection.cursor() as cur:
        cur.execute(
            _UPSERT_SQL,
            {
                "ip": result.ip,
                "country": result.country,
                "country_code": result.country_code,
                "city": result.city,
                "isp": result.isp,
                "asn": result.asn,
                "latitude": result.latitude,
                "longitude": result.longitude,
                "error": result.error,
                "ttl_days": ttl_days,
            },
        )
    connection.commit()
