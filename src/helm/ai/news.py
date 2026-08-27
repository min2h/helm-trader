from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

FEEDS = (
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://www.binance.com/en/support/announcement/rss",
)


def fetch_headlines(limit: int = 8, timeout: float = 12.0) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for url in FEEDS:
        try:
            response = httpx.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except Exception:
            continue
        for node in root.iter():
            if node.tag.lower().endswith("item"):
                title = ""
                link = ""
                for child in node:
                    tag = child.tag.lower()
                    if tag.endswith("title") and child.text:
                        title = child.text.strip()
                    if tag.endswith("link") and child.text:
                        link = child.text.strip()
                if title:
                    items.append({"title": title, "link": link, "source": url})
            if len(items) >= limit:
                return items
    return items[:limit]
