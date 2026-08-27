from helm.settings import Settings


def environment_name(settings: Settings) -> str:
    value = settings.binance_environment.lower()
    if value not in {"demo", "live", "testnet"}:
        raise ValueError("BINANCE_ENVIRONMENT must be demo|live|testnet")
    return value


def missing_live_keys(settings: Settings) -> list[str]:
    missing: list[str] = []
    if not settings.binance_api_key:
        missing.append("BINANCE_API_KEY")
    if not settings.binance_api_secret:
        missing.append("BINANCE_API_SECRET")
    return missing
