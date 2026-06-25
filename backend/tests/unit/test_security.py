from __future__ import annotations

import pytest

from app.domain.identity import Role
from app.infrastructure.config import Settings
from app.infrastructure.security import PasswordManager


def test_argon2id_hash_and_verify() -> None:
    manager = PasswordManager()

    password_hash = manager.hash("correct horse battery staple")

    assert password_hash.startswith("$argon2id$")
    assert manager.verify(password_hash, "correct horse battery staple")
    assert not manager.verify(password_hash, "incorrect")


def test_role_hierarchy() -> None:
    assert Role.ADMIN.allows(Role.ADMIN)
    assert Role.ADMIN.allows(Role.ANALYST)
    assert Role.ANALYST.allows(Role.VIEWER)
    assert not Role.VIEWER.allows(Role.ANALYST)


def test_real_environment_requires_secure_cookies() -> None:
    with pytest.raises(ValueError):
        Settings(environment="real", cookie_secure=False)
