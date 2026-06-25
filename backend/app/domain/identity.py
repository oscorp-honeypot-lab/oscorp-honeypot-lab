from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"

    def allows(self, required: "Role") -> bool:
        rank = {
            Role.VIEWER: 1,
            Role.ANALYST: 2,
            Role.ADMIN: 3,
        }
        return rank[self] >= rank[required]


@dataclass(frozen=True, slots=True)
class UserIdentity:
    id: UUID
    username: str
    password_hash: str
    role: Role
    is_active: bool


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: UUID
    user: UserIdentity
    csrf_token_hash: str
    idle_expires_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True, slots=True)
class SessionCredentials:
    session_token: str
    csrf_token: str
    user: UserIdentity
    expires_at: datetime
