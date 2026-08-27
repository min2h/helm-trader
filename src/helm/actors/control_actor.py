from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from helm.config.schema import Params, RunState, apply_user_patch
from helm.config.store import ParamsStore
from helm.risk.circuit import evaluate_circuit

CommandKind = Literal["soft_stop", "resume", "flat_all", "reload_params"]


@dataclass(frozen=True)
class EngineCommand:
    kind: CommandKind
    reason: str
    at: datetime


@dataclass
class RuntimeStatus:
    heartbeat_at: datetime | None = None
    daily_pnl_pct: float = 0.0
    drawdown_from_peak_pct: float = 0.0
    open_positions: int = 0
    last_command: EngineCommand | None = None
    notes: list[str] = field(default_factory=list)


class ControlActor:
    """Process-local control plane. Does not place orders; the engine consumes commands."""

    def __init__(self, store: ParamsStore) -> None:
        self.store = store
        self._lock = threading.RLock()
        self._params = store.load()
        self._commands: list[EngineCommand] = []
        self._status = RuntimeStatus()
        self._kill_token: str | None = None
        self._kill_expires: datetime | None = None

    def params(self) -> Params:
        with self._lock:
            return self._params

    def status(self) -> RuntimeStatus:
        with self._lock:
            return RuntimeStatus(
                heartbeat_at=self._status.heartbeat_at,
                daily_pnl_pct=self._status.daily_pnl_pct,
                drawdown_from_peak_pct=self._status.drawdown_from_peak_pct,
                open_positions=self._status.open_positions,
                last_command=self._status.last_command,
                notes=list(self._status.notes),
            )

    def heartbeat(
        self,
        *,
        daily_pnl_pct: float | None = None,
        drawdown_from_peak_pct: float | None = None,
        open_positions: int | None = None,
    ) -> None:
        with self._lock:
            self._status.heartbeat_at = datetime.now(timezone.utc)
            if daily_pnl_pct is not None:
                self._status.daily_pnl_pct = daily_pnl_pct
            if drawdown_from_peak_pct is not None:
                self._status.drawdown_from_peak_pct = drawdown_from_peak_pct
            if open_positions is not None:
                self._status.open_positions = open_positions
            decision = evaluate_circuit(
                daily_pnl_pct=self._status.daily_pnl_pct,
                drawdown_from_peak_pct=self._status.drawdown_from_peak_pct,
                limits=self._params.risk,
                run_state=self._params.run_state,
            )
            if decision.action == "hard_kill":
                self._apply_run_state("hard_kill", decision.reason, flat=True)
            elif decision.action == "soft_stop":
                self._apply_run_state("soft_stop", decision.reason, flat=False)

    def patch_params(self, patch: dict) -> Params:
        with self._lock:
            result = apply_user_patch(self._params, patch)
            self._params = self.store.replace(result).params
            self._emit("reload_params", "user_patch")
            if self._params.run_state == "soft_stop":
                self._emit("soft_stop", "user_patch")
            elif self._params.run_state == "running":
                self._emit("resume", "user_patch")
            elif self._params.run_state == "hard_kill":
                self._emit("flat_all", "user_patch")
            return self._params

    def soft_stop(self, reason: str = "user") -> Params:
        with self._lock:
            return self._apply_run_state("soft_stop", reason, flat=False)

    def resume(self, reason: str = "user") -> Params:
        with self._lock:
            if self._params.run_state == "hard_kill" and self._status.open_positions > 0:
                raise RuntimeError("cannot resume hard_kill while positions are open")
            return self._apply_run_state("running", reason, flat=False)

    def prepare_hard_kill(self) -> dict[str, str | int]:
        with self._lock:
            self._kill_token = secrets.token_urlsafe(16)
            self._kill_expires = datetime.now(timezone.utc) + timedelta(seconds=5)
            return {"token": self._kill_token, "expires_in_sec": 5}

    def confirm_hard_kill(self, token: str, reason: str = "user") -> Params:
        with self._lock:
            now = datetime.now(timezone.utc)
            if (
                not self._kill_token
                or token != self._kill_token
                or self._kill_expires is None
                or now > self._kill_expires
            ):
                raise PermissionError("hard_kill token invalid or expired")
            self._kill_token = None
            self._kill_expires = None
            return self._apply_run_state("hard_kill", reason, flat=True)

    def approve_symbol(self, symbol: str) -> Params:
        symbol = symbol.strip().upper()
        with self._lock:
            active = list(self._params.symbols.active)
            pending = [s for s in self._params.symbols.pending_approval if s != symbol]
            if symbol and symbol not in active:
                active.append(symbol)
            result = apply_user_patch(self._params, {"symbols.active": active})
            data = result.params.model_dump()
            data["symbols"]["pending_approval"] = pending
            from helm.config.schema import clamp_params

            clamped = clamp_params(data)
            self._params = self.store.replace(clamped).params
            self._emit("reload_params", "symbol_approve")
            return self._params

    def drain_commands(self) -> list[EngineCommand]:
        with self._lock:
            commands = list(self._commands)
            self._commands.clear()
            return commands

    def _apply_run_state(self, state: RunState, reason: str, *, flat: bool) -> Params:
        if self._params.run_state != state:
            result = apply_user_patch(self._params, {"run_state": state})
            self._params = self.store.replace(result).params
        if flat:
            self._emit("flat_all", reason)
        elif state == "soft_stop":
            self._emit("soft_stop", reason)
        elif state == "running":
            self._emit("resume", reason)
        return self._params

    def _emit(self, kind: CommandKind, reason: str) -> None:
        command = EngineCommand(kind=kind, reason=reason, at=datetime.now(timezone.utc))
        self._commands.append(command)
        self._status.last_command = command
        self._status.notes.append(f"{kind}:{reason}")
