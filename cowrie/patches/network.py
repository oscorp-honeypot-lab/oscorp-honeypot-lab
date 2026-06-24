# SPDX-FileCopyrightText: 2025-2026 Michel Oosterhof <michel@oosterhof.net>
# SPDX-License-Identifier: BSD-3-Clause
"""Cowrie network policy with an explicit LAB-only hostname allowlist."""

import ipaddress
import os
import re
from collections.abc import Generator

from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.names import client, dns
from twisted.python import log


BLOCKED_IPS = [
    "0.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "100.100.100.200",
    "127.0.0.0/8",
    "224.0.0.0/4",
    "240.0.0.0/4",
    "255.255.255.255",
    "::1",
]

PORT_PATTERN = re.compile(
    r"^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|"
    r"65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$"
)


def _allowed_lab_hosts() -> set[str]:
    raw_hosts = os.environ.get("COWRIE_LAB_ALLOWED_DOWNLOAD_HOSTS", "")
    return {
        host.strip().lower().rstrip(".")
        for host in raw_hosts.split(",")
        if host.strip()
    }


def is_valid_port(port: str) -> bool:
    return bool(PORT_PATTERN.match(port))


def is_ip_address(
    address: str,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(address)
    except ValueError:
        return None


@inlineCallbacks
def resolve_cname(
    address: str,
    visited: set[str],
) -> Generator[Deferred, None, str | None]:
    log.msg(f"resolve_cname({address})")
    if address in visited:
        return None
    visited.add(address)

    try:
        result = yield client.lookupAddress(address)
        if result:
            headers: list[dns.RRHeader] = result[0]  # type: ignore
            for rr in headers:
                if isinstance(rr.payload, dns.Record_CNAME):
                    resolved_ip = yield resolve_cname(str(rr.payload.name), visited)
                    if resolved_ip:
                        return resolved_ip
                elif isinstance(rr.payload, dns.Record_A):
                    return str(rr.payload.dottedQuad())
                elif isinstance(rr.payload, dns.Record_AAAA):
                    return str(rr.payload.dottedQuad())
    except Exception as exc:
        log.err(exc)
        return None

    return None


@inlineCallbacks
def communication_allowed(address: str) -> Generator[Deferred, None, bool]:
    normalized = address.lower().rstrip(".")
    if normalized in _allowed_lab_hosts():
        log.msg(f"LAB download host explicitly allowed: {normalized}")
        return True

    ip = is_ip_address(address)
    if ip is not None:
        resolved_ip = str(ip)
    else:
        result = yield resolve_cname(address, set())
        if result is None:
            return False
        resolved_ip = result

    try:
        ip = ipaddress.ip_address(resolved_ip)
        for blocked in BLOCKED_IPS:
            if ip in ipaddress.ip_network(blocked, strict=False):
                return False
    except ValueError:
        return False

    return True
