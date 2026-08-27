from __future__ import annotations

import httpx

from helm.ai.news import fetch_headlines
from helm.ai.prompt import ANALYSIS_TASK, CHAT_GUARD
from helm.config.schema import Params


def fetch_market_snapshot(symbols: list[str] | None = None) -> dict:
    symbols = symbols or ["BTCUSDT", "ETHUSDT"]
    tickers: list[dict] = []
    funding: list[dict] = []
    try:
        rows = httpx.get("https://fapi.binance.com/fapi/v1/ticker/24hr", timeout=12).json()
        wanted = {s.upper() for s in symbols}
        for row in rows:
            if row.get("symbol") in wanted:
                tickers.append(
                    {
                        "symbol": row["symbol"],
                        "last": row.get("lastPrice"),
                        "change_pct": row.get("priceChangePercent"),
                        "quote_volume": row.get("quoteVolume"),
                        "high": row.get("highPrice"),
                        "low": row.get("lowPrice"),
                    }
                )
    except Exception:
        pass
    for symbol in symbols[:6]:
        try:
            row = httpx.get(
                "https://fapi.binance.com/fapi/v1/premiumIndex",
                params={"symbol": symbol.upper()},
                timeout=8,
            ).json()
            funding.append(
                {
                    "symbol": symbol.upper(),
                    "mark": row.get("markPrice"),
                    "index": row.get("indexPrice"),
                    "last_funding": row.get("lastFundingRate"),
                }
            )
        except Exception:
            continue
    return {"tickers": tickers, "funding": funding}


def build_analysis_prompt(params: Params, daily_pnl_pct: float) -> tuple[str, list[dict]]:
    headlines = fetch_headlines(limit=12)
    snap = fetch_market_snapshot(params.symbols.active or ["BTCUSDT", "ETHUSDT"])
    news = "\n".join(f"- {item['title']}" for item in headlines) or "- (뉴스 피드 없음)"
    body = (
        f"{ANALYSIS_TASK}\n"
        f"run_state={params.run_state} strategy={params.strategy_mode} "
        f"risk_grade={params.risk_grade} market={params.market_mode} "
        f"daily_pnl_pct={daily_pnl_pct} min_equity={params.risk.min_equity_usdt}\n"
        f"active={params.symbols.active} pending={params.symbols.pending_approval}\n"
        f"trend={params.strategy.trend.model_dump()}\n"
        f"funding_arb={params.strategy.funding_arb.model_dump()}\n"
        f"grid={params.strategy.grid.model_dump()}\n"
        f"risk={params.risk.model_dump()}\n"
        f"manual_band={params.manual_band.model_dump()}\n"
        f"24h tickers={snap['tickers']}\n"
        f"funding/mark={snap['funding']}\n"
        f"headlines:\n{news}\n"
    )
    return body, headlines


def build_chat_prompt(params: Params, user_text: str) -> str:
    return (
        f"{CHAT_GUARD}{user_text}\n\n"
        f"[엔진 스냅샷] run_state={params.run_state} strategy={params.strategy_mode} "
        f"risk_grade={params.risk_grade} leverage<={params.risk.leverage} "
        f"active={params.symbols.active} stop_style={params.stop_style}"
    )
