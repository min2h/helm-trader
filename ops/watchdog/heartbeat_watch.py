#!/usr/bin/env python3
"""VPS-side heartbeat watcher. No exchange keys. Alerts only."""

from __future__ import annotations

import os
import time
import urllib.request


def main() -> None:
    url = os.environ["HELM_STATUS_URL"]
    token = os.environ.get("HELM_TOKEN", "")
    timeout_sec = int(os.environ.get("HELM_WATCH_TIMEOUT", "90"))
    last_ok = time.time()
    while True:
        try:
            req = urllib.request.Request(url, headers={"X-Helm-Token": token})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    last_ok = time.time()
        except Exception as exc:  # noqa: BLE001
            print("watch_error", exc)
        if time.time() - last_ok > timeout_sec:
            print("HEARTBEAT_LOST exchange-side stops only")
        time.sleep(15)


if __name__ == "__main__":
    main()
