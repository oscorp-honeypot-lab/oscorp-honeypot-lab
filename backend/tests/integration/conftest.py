from __future__ import annotations

import os

import psycopg
import pytest


def _database_dsn() -> str:
    return os.environ["OSCORP_API_DATABASE_URL"].replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )


def _reset_login_attempts() -> None:
    """Delete login attempts recorded by TestClient so rate-limiter state
    does not bleed between tests or across pytest runs."""
    with psycopg.connect(_database_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM app_login_attempts WHERE client_ip = 'testclient'"
            )


@pytest.fixture(autouse=True)
def clean_login_attempts():
    _reset_login_attempts()
    yield
    _reset_login_attempts()
