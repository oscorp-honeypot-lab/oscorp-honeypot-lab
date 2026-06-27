from __future__ import annotations

import secrets
from hashlib import sha256

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type


class PasswordManager:
    def __init__(self) -> None:
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )
        self._dummy_hash = self._hasher.hash("invalid-password-placeholder")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str | None, password: str) -> bool:
        candidate = password_hash or self._dummy_hash
        try:
            return self._hasher.verify(candidate, password) and password_hash is not None
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def hash_secret(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def secrets_match(left: str, right: str) -> bool:
    return secrets.compare_digest(left, right)
