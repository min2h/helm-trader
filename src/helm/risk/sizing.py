def position_qty(
    equity: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
    leverage: int = 1,
) -> float:
    """Size so a stop hit loses at most equity * risk_pct.

    Leverage does not increase the dollar risk; it only reduces required margin.
    """
    if equity <= 0 or risk_pct <= 0 or entry_price <= 0:
        return 0.0
    stop_distance = abs(entry_price - stop_price)
    if stop_distance <= 0:
        return 0.0
    risk_budget = equity * (risk_pct / 100.0)
    qty = risk_budget / stop_distance
    notional = qty * entry_price
    max_notional = equity * max(leverage, 1)
    if notional > max_notional:
        qty = max_notional / entry_price
    return max(qty, 0.0)
