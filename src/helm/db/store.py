from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from helm.auth.crypto import SecretBox
from helm.db.models import User, now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    subject TEXT NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    nickname TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'pending',
    notify_email INTEGER NOT NULL DEFAULT 1,
    notify_telegram INTEGER NOT NULL DEFAULT 0,
    theme TEXT NOT NULL DEFAULT 'dark',
    min_equity_usdt REAL NOT NULL DEFAULT 0,
    notify_address TEXT NOT NULL DEFAULT '',
    telegram_chat_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(provider, subject)
);
CREATE TABLE IF NOT EXISTS user_secrets (
    user_id INTEGER PRIMARY KEY,
    binance_key TEXT NOT NULL DEFAULT '',
    binance_secret TEXT NOT NULL DEFAULT '',
    llm_provider TEXT NOT NULL DEFAULT '',
    llm_key TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS manual_jobs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL DEFAULT 'BUY',
    lower REAL NOT NULL,
    upper REAL NOT NULL,
    schedule TEXT NOT NULL DEFAULT 'every_15m',
    size_usdt REAL NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'manual',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    markdown TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_attempts (
    ip TEXT PRIMARY KEY,
    failures INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT
);
CREATE TABLE IF NOT EXISTS market_symbols (
    symbol TEXT NOT NULL,
    base TEXT NOT NULL,
    quote TEXT NOT NULL,
    market TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'TRADING',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (symbol, market)
);
CREATE INDEX IF NOT EXISTS idx_market_symbols_quote ON market_symbols(quote);
CREATE TABLE IF NOT EXISTS ai_runs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT 'autopilot',
    regime TEXT NOT NULL DEFAULT '',
    symbols TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_ai_runs_user ON ai_runs(user_id, id);
"""

MIGRATIONS = {
    "manual_jobs": {
        "source": "ALTER TABLE manual_jobs ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'",
        "note": "ALTER TABLE manual_jobs ADD COLUMN note TEXT NOT NULL DEFAULT ''",
    },
}


def _secret_hint(value: str) -> str:
    if not value:
        return ""
    tail = value[-4:] if len(value) >= 4 else value
    return f"{'•' * max(8, min(len(value) - 4, 16))}{tail}"


def _locked(fn):
    @wraps(fn)
    def inner(self, *args, **kwargs):
        with self._lock:
            return fn(self, *args, **kwargs)

    return inner


def _row_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        provider=row["provider"],
        subject=row["subject"],
        email=row["email"],
        nickname=row["nickname"],
        role=row["role"],
        status=row["status"],
        notify_email=bool(row["notify_email"]),
        notify_telegram=bool(row["notify_telegram"]),
        theme=row["theme"],
        min_equity_usdt=float(row["min_equity_usdt"]),
        notify_address=row["notify_address"],
        telegram_chat_id=row["telegram_chat_id"],
        created_at=row["created_at"],
    )


class Database:
    def __init__(self, path: Path, box: SecretBox) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.box = box
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Older DB files miss columns added later; SQLite needs one ALTER per column."""
        for table, columns in MIGRATIONS.items():
            have = {row["name"] for row in self._conn.execute(f"PRAGMA table_info({table})")}
            for column, statement in columns.items():
                if column not in have:
                    self._conn.execute(statement)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert_oauth_user(
        self,
        *,
        provider: str,
        subject: str,
        email: str,
        nickname: str,
        admin_emails: set[str],
    ) -> User:
        existing = self._conn.execute(
            "SELECT * FROM users WHERE provider=? AND subject=?",
            (provider, subject),
        ).fetchone()
        if existing:
            return _row_user(existing)
        is_admin = email.lower() in admin_emails
        role = "admin" if is_admin else "user"
        status = "approved" if is_admin else "pending"
        self._conn.execute(
            """INSERT INTO users (provider, subject, email, nickname, role, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (provider, subject, email, nickname or email.split("@")[0], role, status, now_iso()),
        )
        self._conn.commit()
        user = self.get_user_by_subject(provider, subject)
        assert user
        self.audit(user.id, "signup", f"{provider}:{email}:{status}")
        return user

    def get_user(self, user_id: int) -> User | None:
        row = self._conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return _row_user(row) if row else None

    def get_user_by_subject(self, provider: str, subject: str) -> User | None:
        row = self._conn.execute(
            "SELECT * FROM users WHERE provider=? AND subject=?",
            (provider, subject),
        ).fetchone()
        return _row_user(row) if row else None

    def list_users(self) -> list[User]:
        rows = self._conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [_row_user(row) for row in rows]

    def set_status(self, user_id: int, status: str) -> User:
        self._conn.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
        self._conn.commit()
        user = self.get_user(user_id)
        assert user
        self.audit(user_id, "status", status)
        return user

    def update_profile(self, user_id: int, fields: dict) -> User:
        allowed = {
            "nickname",
            "notify_email",
            "notify_telegram",
            "theme",
            "min_equity_usdt",
            "notify_address",
            "telegram_chat_id",
        }
        sets: list[str] = []
        values: list[object] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key in {"notify_email", "notify_telegram"}:
                value = 1 if value else 0
            sets.append(f"{key}=?")
            values.append(value)
        if sets:
            values.append(user_id)
            self._conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", values)
            self._conn.commit()
        user = self.get_user(user_id)
        assert user
        return user

    def create_session(self, user_id: int, hours: int = 24 * 14) -> str:
        import secrets

        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
        self._conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires),
        )
        self._conn.commit()
        return token

    def user_for_session(self, token: str) -> User | None:
        if not token:
            return None
        row = self._conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",
            (token,),
        ).fetchone()
        if not row:
            return None
        expires = self._conn.execute(
            "SELECT expires_at FROM sessions WHERE token=?", (token,)
        ).fetchone()
        if expires and expires["expires_at"] < datetime.now(timezone.utc).isoformat():
            self._conn.execute("DELETE FROM sessions WHERE token=?", (token,))
            self._conn.commit()
            return None
        return _row_user(row)

    def delete_session(self, token: str) -> None:
        self._conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        self._conn.commit()

    def save_oauth_state(self, state: str, provider: str) -> None:
        self._conn.execute(
            "INSERT INTO oauth_states (state, provider, created_at) VALUES (?, ?, ?)",
            (state, provider, now_iso()),
        )
        self._conn.commit()

    def pop_oauth_state(self, state: str) -> str | None:
        row = self._conn.execute("SELECT provider FROM oauth_states WHERE state=?", (state,)).fetchone()
        if not row:
            return None
        self._conn.execute("DELETE FROM oauth_states WHERE state=?", (state,))
        self._conn.commit()
        return str(row["provider"])

    def put_secrets(self, user_id: int, **fields: str) -> None:
        current = self._conn.execute(
            "SELECT * FROM user_secrets WHERE user_id=?", (user_id,)
        ).fetchone()
        data = {
            "binance_key": current["binance_key"] if current else "",
            "binance_secret": current["binance_secret"] if current else "",
            "llm_provider": current["llm_provider"] if current else "",
            "llm_key": current["llm_key"] if current else "",
        }
        mapping = {
            "binance_key": "binance_key",
            "binance_secret": "binance_secret",
            "llm_provider": "llm_provider",
            "llm_key": "llm_key",
        }
        for raw_key, column in mapping.items():
            if raw_key in fields and fields[raw_key]:
                data[column] = (
                    fields[raw_key] if column == "llm_provider" else self.box.encrypt(fields[raw_key])
                )
        self._conn.execute(
            """INSERT INTO user_secrets (user_id, binance_key, binance_secret, llm_provider, llm_key)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 binance_key=excluded.binance_key,
                 binance_secret=excluded.binance_secret,
                 llm_provider=excluded.llm_provider,
                 llm_key=excluded.llm_key""",
            (user_id, data["binance_key"], data["binance_secret"], data["llm_provider"], data["llm_key"]),
        )
        self._conn.commit()
        self.audit(user_id, "secrets", "updated")

    def secret_flags(self, user_id: int) -> dict[str, bool | str]:
        plain = self.decrypt_secrets(user_id)
        return {
            "binance": bool(plain["binance_key"] and plain["binance_secret"]),
            "llm": bool(plain["llm_key"]),
            "llm_provider": plain["llm_provider"],
            "llm_hint": _secret_hint(plain["llm_key"]),
            "binance_key_hint": _secret_hint(plain["binance_key"]),
            "binance_secret_hint": _secret_hint(plain["binance_secret"]),
        }

    def decrypt_secrets(self, user_id: int) -> dict[str, str]:
        row = self._conn.execute("SELECT * FROM user_secrets WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return {"binance_key": "", "binance_secret": "", "llm_provider": "", "llm_key": ""}
        return {
            "binance_key": self.box.decrypt(row["binance_key"]),
            "binance_secret": self.box.decrypt(row["binance_secret"]),
            "llm_provider": row["llm_provider"],
            "llm_key": self.box.decrypt(row["llm_key"]),
        }

    def add_manual_job(self, user_id: int, payload: dict) -> dict:
        cur = self._conn.execute(
            """INSERT INTO manual_jobs
               (user_id, symbol, side, lower, upper, schedule, size_usdt, enabled, source, note, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                str(payload["symbol"]).upper(),
                str(payload.get("side", "BUY")).upper(),
                float(payload["lower"]),
                float(payload["upper"]),
                str(payload.get("schedule", "every_15m")),
                float(payload.get("size_usdt", 100)),
                1 if payload.get("enabled", True) else 0,
                "ai" if str(payload.get("source", "manual")) == "ai" else "manual",
                str(payload.get("note", "")),
                now_iso(),
            ),
        )
        self._conn.commit()
        return self.get_manual_job(int(cur.lastrowid))

    def get_manual_job(self, job_id: int) -> dict:
        row = self._conn.execute("SELECT * FROM manual_jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else {}

    def list_manual_jobs(self, user_id: int) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM manual_jobs WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def list_manual_jobs_by_source(self, user_id: int, source: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM manual_jobs WHERE user_id=? AND source=? ORDER BY id DESC",
            (user_id, source),
        ).fetchall()
        return [dict(row) for row in rows]

    def disable_manual_jobs(self, user_id: int, source: str) -> int:
        cur = self._conn.execute(
            "UPDATE manual_jobs SET enabled=0 WHERE user_id=? AND source=? AND enabled=1",
            (user_id, source),
        )
        self._conn.commit()
        return int(cur.rowcount or 0)

    def delete_manual_jobs(self, user_id: int, source: str) -> int:
        cur = self._conn.execute(
            "DELETE FROM manual_jobs WHERE user_id=? AND source=?", (user_id, source)
        )
        self._conn.commit()
        return int(cur.rowcount or 0)

    def set_manual_enabled(self, user_id: int, job_id: int, enabled: bool) -> dict:
        self._conn.execute(
            "UPDATE manual_jobs SET enabled=? WHERE id=? AND user_id=?",
            (1 if enabled else 0, job_id, user_id),
        )
        self._conn.commit()
        return self.get_manual_job(job_id)

    def delete_manual_job(self, user_id: int, job_id: int) -> None:
        self._conn.execute("DELETE FROM manual_jobs WHERE id=? AND user_id=?", (job_id, user_id))
        self._conn.commit()

    def add_ai_run(
        self,
        user_id: int,
        *,
        symbols: list[str],
        regime: str = "",
        detail: str = "",
        kind: str = "autopilot",
    ) -> dict:
        cur = self._conn.execute(
            """INSERT INTO ai_runs (user_id, kind, regime, symbols, detail, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, kind, regime, ",".join(s.upper() for s in symbols), detail, now_iso()),
        )
        self._conn.commit()
        return {"id": int(cur.lastrowid), "symbols": symbols, "regime": regime}

    def list_ai_runs(self, user_id: int, limit: int = 5, kind: str = "autopilot") -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM ai_runs WHERE user_id=? AND kind=? ORDER BY id DESC LIMIT ?",
            (user_id, kind, limit),
        ).fetchall()
        out: list[dict] = []
        for row in rows:
            item = dict(row)
            item["symbols"] = [s for s in str(row["symbols"]).split(",") if s]
            out.append(item)
        return out

    def recent_ai_symbols(self, user_id: int, runs: int = 3, kind: str = "autopilot") -> list[str]:
        seen: list[str] = []
        for run in self.list_ai_runs(user_id, limit=runs, kind=kind):
            for symbol in run["symbols"]:
                if symbol not in seen:
                    seen.append(symbol)
        return seen

    def add_report(self, user_id: int, kind: str, markdown: str) -> dict:
        cur = self._conn.execute(
            "INSERT INTO reports (user_id, kind, markdown, created_at) VALUES (?, ?, ?, ?)",
            (user_id, kind, markdown, now_iso()),
        )
        self._conn.commit()
        return {"id": cur.lastrowid, "kind": kind, "markdown": markdown}

    def latest_report(self, user_id: int, kind: str | None = None) -> dict | None:
        if kind:
            row = self._conn.execute(
                "SELECT * FROM reports WHERE user_id=? AND kind=? ORDER BY id DESC LIMIT 1",
                (user_id, kind),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT * FROM reports WHERE user_id=? ORDER BY id DESC LIMIT 1",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def add_chat(self, user_id: int, role: str, content: str) -> None:
        self._conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, now_iso()),
        )
        self._conn.commit()

    def list_chat(self, user_id: int, limit: int = 40) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM chat_messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def audit(self, user_id: int | None, action: str, detail: str) -> None:
        self._conn.execute(
            "INSERT INTO audit_log (user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, detail, now_iso()),
        )
        self._conn.commit()

    def register_failure(self, ip: str, max_failures: int = 8) -> bool:
        row = self._conn.execute("SELECT * FROM login_attempts WHERE ip=?", (ip,)).fetchone()
        now = datetime.now(timezone.utc)
        if row and row["locked_until"] and row["locked_until"] > now.isoformat():
            return True
        failures = (row["failures"] if row else 0) + 1
        locked = (now + timedelta(minutes=15)).isoformat() if failures >= max_failures else None
        self._conn.execute(
            """INSERT INTO login_attempts (ip, failures, locked_until) VALUES (?, ?, ?)
               ON CONFLICT(ip) DO UPDATE SET failures=?, locked_until=?""",
            (ip, failures, locked, failures, locked),
        )
        self._conn.commit()
        return bool(locked)

    def is_locked(self, ip: str) -> bool:
        row = self._conn.execute("SELECT locked_until FROM login_attempts WHERE ip=?", (ip,)).fetchone()
        if not row or not row["locked_until"]:
            return False
        return str(row["locked_until"]) > datetime.now(timezone.utc).isoformat()

    def clear_failures(self, ip: str) -> None:
        self._conn.execute("DELETE FROM login_attempts WHERE ip=?", (ip,))
        self._conn.commit()

    def replace_market_symbols(self, rows: list[dict]) -> int:
        stamp = now_iso()
        self._conn.execute("DELETE FROM market_symbols")
        self._conn.executemany(
            """INSERT INTO market_symbols (symbol, base, quote, market, status, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (
                    str(row["symbol"]).upper(),
                    str(row.get("base") or ""),
                    str(row.get("quote") or ""),
                    str(row.get("market") or "spot"),
                    str(row.get("status") or "TRADING"),
                    stamp,
                )
                for row in rows
            ],
        )
        self._conn.commit()
        return len(rows)

    def list_market_symbols(self, market: str = "all", q: str = "", limit: int = 8000) -> list[dict]:
        where = ["1=1"]
        args: list[object] = []
        if market in {"spot", "futures"}:
            where.append("market=?")
            args.append(market)
        if q.strip():
            needle = f"%{q.strip().upper()}%"
            where.append("(symbol LIKE ? OR base LIKE ? OR quote LIKE ?)")
            args.extend([needle, needle, needle])
        args.append(max(1, min(int(limit), 12000)))
        rows = self._conn.execute(
            f"SELECT symbol, base, quote, market, status FROM market_symbols WHERE {' AND '.join(where)} "
            "ORDER BY CASE quote WHEN 'USDT' THEN 0 WHEN 'USDC' THEN 1 ELSE 2 END, symbol LIMIT ?",
            args,
        ).fetchall()
        return [dict(row) for row in rows]

    def market_symbol_count(self, market: str = "all") -> int:
        if market in {"spot", "futures"}:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM market_symbols WHERE market=?", (market,)).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM market_symbols").fetchone()
        return int(row["n"] if row else 0)

    def market_symbols_updated_at(self) -> str | None:
        row = self._conn.execute("SELECT MAX(updated_at) AS ts FROM market_symbols").fetchone()
        return str(row["ts"]) if row and row["ts"] else None


for _name, _fn in list(vars(Database).items()):
    if _name == "__init__" or _name.startswith("_") or not callable(_fn):
        continue
    setattr(Database, _name, _locked(_fn))
