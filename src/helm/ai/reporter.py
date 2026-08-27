from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from helm.config.schema import Params


def render_daily_report(
    params: Params,
    *,
    daily_pnl_pct: float,
    trades: int,
    ai_status: str,
    notes: list[str],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    note_lines = "\n".join(f"- {n}" for n in notes) or "- none"
    return (
        f"# helm daily report\n\n"
        f"- time: {now}\n"
        f"- run_state: {params.run_state}\n"
        f"- strategy: {params.strategy_mode}\n"
        f"- risk_grade: {params.risk_grade}\n"
        f"- daily_pnl_pct: {daily_pnl_pct:.2f}\n"
        f"- trades: {trades}\n"
        f"- ai_status: {ai_status}\n"
        f"- active: {', '.join(params.symbols.active)}\n\n"
        f"## notes\n{note_lines}\n"
    )


def write_report(text: str, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    path.write_text(text, encoding="utf-8")
    return path
