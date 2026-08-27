from typing import Any


def close_position_stop(
    *,
    symbol: str,
    side: str,
    trigger_price: float,
    working_type: str = "MARK_PRICE",
) -> dict[str, Any]:
    """Binance / Nautilus params for a venue-held full-position stop.

    Mac mini downtime does not cancel this order. Do not combine with reduce_only.
    """
    close_side = "SELL" if side.upper() == "BUY" else "BUY"
    return {
        "symbol": symbol.upper(),
        "side": close_side,
        "type": "STOP_MARKET",
        "stopPrice": trigger_price,
        "closePosition": True,
        "workingType": working_type,
        "params": {"close_position": True},
    }
