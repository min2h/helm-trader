import httpx

from helm.research.http import get_json


class _Ok:
    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {"ok": True}


def test_get_json_falls_back_when_ssl_fails(monkeypatch) -> None:
    calls: list[bool] = []

    def fake_get(url, params=None, timeout=20, verify=True, follow_redirects=False, headers=None):
        calls.append(verify)
        if verify:
            raise httpx.ConnectError("SSL")
        return _Ok()

    monkeypatch.setattr("helm.research.http.httpx.get", fake_get)
    assert get_json("https://example.test") == {"ok": True}
    assert calls == [True, False]


def test_first_json_uses_next_host(monkeypatch) -> None:
    from helm.research.http import first_json

    def fake_get(url, params=None, timeout=20, verify=True, follow_redirects=False, headers=None):
        if "blocked" in url:
            raise httpx.ConnectError("blocked")
        return _Ok()

    monkeypatch.setattr("helm.research.http.httpx.get", fake_get)
    assert first_json(["https://blocked.test", "https://ok.test"]) == {"ok": True}
