from dataclasses import dataclass


@dataclass(frozen=True)
class GridPlan:
    prices: list[float]
    blocked: bool


def build_grid(
    mid: float,
    atr_value: float,
    *,
    levels: int,
    atr_mult: float,
    inventory_pct: float,
    max_inventory_pct: float,
) -> GridPlan:
    if inventory_pct >= max_inventory_pct:
        return GridPlan([], True)
    step = atr_value * atr_mult
    prices = [mid - step * i for i in range(1, levels + 1)]
    return GridPlan(prices, False)
