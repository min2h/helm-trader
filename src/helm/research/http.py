from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)
_SYSTEM_CERTS = False
_GOOD_HOSTS: set[str] = set()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) helm-trader/0.2",
    "Accept": "application/json,text/plain,*/*",
}


def use_system_certs() -> None:
    global _SYSTEM_CERTS
    if _SYSTEM_CERTS:
        return
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:
        pass
    _SYSTEM_CERTS = True


def get(
    url: str,
    *,
    params: dict | None = None,
    timeout: float = 20.0,
    follow_redirects: bool = False,
) -> httpx.Response:
    """Public HTTPS get. Local SSL inspect + Binance 403 need a fallback host."""
    use_system_certs()
    last: Exception | None = None
    for verify in (True, False):
        try:
            response = httpx.get(
                url,
                params=params,
                timeout=timeout,
                verify=verify,
                follow_redirects=follow_redirects,
                headers=HEADERS,
            )
            response.raise_for_status()
            if not verify:
                log.warning("TLS verify skipped for %s (proxy/antivirus cert)", url)
            return response
        except Exception as exc:
            last = exc
    raise last or RuntimeError(f"GET {url} failed")


def get_json(url: str, params: dict | None = None, timeout: float = 20.0):
    return get(url, params=params, timeout=timeout).json()


def first_json(urls: list[str], params: dict | None = None, timeout: float = 20.0):
    last: Exception | None = None
    ordered = [url for url in urls if url in _GOOD_HOSTS] + [url for url in urls if url not in _GOOD_HOSTS]
    for url in ordered:
        try:
            payload = get_json(url, params=params, timeout=timeout)
            _GOOD_HOSTS.add(url)
            return payload
        except Exception as exc:
            last = exc
            _GOOD_HOSTS.discard(url)
            log.warning("market fetch missed %s: %s", url, exc)
    raise last or RuntimeError("all market hosts failed")
