from helm.engine.binance import environment_name, missing_live_keys
from helm.settings import Settings


class EngineUnavailable(RuntimeError):
    pass


def run_live_node(settings: Settings) -> None:
    """Phase 2: boot Nautilus TradingNode. Phase 0 only checks prerequisites."""
    missing = missing_live_keys(settings)
    if missing:
        raise EngineUnavailable(f"missing keys: {', '.join(missing)}")
    env = environment_name(settings)
    try:
        import nautilus_trader  # noqa: F401
    except ImportError as exc:
        raise EngineUnavailable(
            "nautilus_trader is not installed. pip install 'helm-trader[engine]'"
        ) from exc
    raise EngineUnavailable(
        f"live TradingNode wiring is Phase 2. credentials/env={env} look present."
    )
