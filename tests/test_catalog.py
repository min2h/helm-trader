from helm.research.catalog import FALLBACK, catalog_from_exchange_info


def test_catalog_filters_usdt_perpetual() -> None:
    payload = {
        "symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT", "contractType": "PERPETUAL"},
            {"symbol": "ETHUSDT", "status": "BREAK", "baseAsset": "ETH", "quoteAsset": "USDT", "contractType": "PERPETUAL"},
            {"symbol": "BTCUSDC", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDC", "contractType": "PERPETUAL"},
            {"symbol": "BTCUSDT_Q", "status": "TRADING", "baseAsset": "BTC", "quoteAsset": "USDT", "contractType": "CURRENT_QUARTER"},
        ]
    }
    items = catalog_from_exchange_info(payload, "futures")
    assert [row["symbol"] for row in items] == ["BTCUSDT"]
    assert FALLBACK[0]["symbol"] == "BTCUSDT"
