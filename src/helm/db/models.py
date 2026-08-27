from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

UserStatus = Literal["pending", "approved", "suspended"]
UserRole = Literal["user", "admin"]


@dataclass
class User:
    id: int
    provider: str
    subject: str
    email: str
    nickname: str
    role: UserRole
    status: UserStatus
    notify_email: bool
    notify_telegram: bool
    theme: str
    min_equity_usdt: float
    notify_address: str
    telegram_chat_id: str
    created_at: str

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "email": self.email,
            "nickname": self.nickname or self.email.split("@")[0],
            "role": self.role,
            "status": self.status,
            "notify_email": self.notify_email,
            "notify_telegram": self.notify_telegram,
            "theme": self.theme,
            "min_equity_usdt": self.min_equity_usdt,
            "notify_address": self.notify_address,
            "telegram_configured": bool(self.telegram_chat_id),
            "created_at": self.created_at,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
