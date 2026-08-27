from dataclasses import dataclass


@dataclass(frozen=True)
class FundingSignal:
    enter: bool
    exit: bool
    reason: str


def evaluate_funding(
    *,
    funding_apr: float,
    basis_bps: float,
    min_funding_apr: float,
    max_basis_bps: float,
) -> FundingSignal:
    if funding_apr >= min_funding_apr and abs(basis_bps) <= max_basis_bps:
        return FundingSignal(True, False, "funding_rich")
    if funding_apr < min_funding_apr * 0.5 or abs(basis_bps) > max_basis_bps * 2:
        return FundingSignal(False, True, "funding_or_basis_dead")
    return FundingSignal(False, False, "hold")
