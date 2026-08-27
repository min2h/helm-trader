from helm.config.schema import Params
from helm.config.store import ParamsStore


def test_atomic_roundtrip(tmp_path) -> None:
    store = ParamsStore(tmp_path / "params.json")
    params = Params(strategy_mode="grid")
    store.save(params)
    loaded = store.load()
    assert loaded.strategy_mode == "grid"
    assert store.prev_path.exists() or loaded.version == 1
