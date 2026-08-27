from helm.auth.crypto import SecretBox
from helm.db.store import Database
from helm.research.catalog import catalog_from_exchange_info
from helm.research.fx import _parse_usd_krw


def test_catalog_keeps_all_quotes_and_skips_non_perps() -> None:
    payload = {
        "symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT", "contractType": "PERPETUAL"},
            {"symbol": "ETHUSDT", "status": "BREAK", "baseAsset": "ETH", "quoteAsset": "USDT", "contractType": "PERPETUAL"},
            {"symbol": "BTCUSDC", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDC", "contractType": "PERPETUAL"},
            {"symbol": "BTCUSDT_Q", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT", "contractType": "CURRENT_QUARTER"},
        ]
    }
    items = catalog_from_exchange_info(payload, "futures")
    assert [row["symbol"] for row in items] == ["BTCUSDT", "BTCUSDC"]


def test_spot_catalog_includes_non_usdt() -> None:
    payload = {
        "symbols": [
            {"symbol": "ETHBTC", "status": "TRADING", "baseAsset": "ETH", "quoteAsset": "BTC"},
            {"symbol": "BTCKRW", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "KRW"},
        ]
    }
    items = catalog_from_exchange_info(payload, "spot")
    assert {row["symbol"] for row in items} == {"ETHBTC", "BTCKRW"}


def test_symbols_persist_in_sqlite(tmp_path) -> None:
    db = Database(tmp_path / "helm.db", SecretBox("", tmp_path / ".master_key"))
    db.replace_market_symbols(
        [
            {"symbol": "AAAUSDT", "base": "AAA", "quote": "USDT", "market": "spot"},
            {"symbol": "AAAUSDT", "base": "AAA", "quote": "USDT", "market": "futures"},
        ]
    )
    assert db.market_symbol_count() == 2
    assert db.market_symbol_count("futures") == 1
    assert db.list_market_symbols("spot")[0]["symbol"] == "AAAUSDT"


def test_parse_usd_krw() -> None:
    assert _parse_usd_krw({"rates": {"KRW": 1390.5}}) == 1390.5
    assert _parse_usd_krw({"foo": 1}) is None
