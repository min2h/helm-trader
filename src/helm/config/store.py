from __future__ import annotations

import json
from pathlib import Path

from helm.config.schema import ClampResult, Params, clamp_params


class ParamsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.prev_path = path.with_suffix(path.suffix + ".prev")
        self.tmp_path = path.with_suffix(path.suffix + ".tmp")

    def load(self) -> Params:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                return clamp_params(raw).params
            except (json.JSONDecodeError, ValueError):
                if self.prev_path.exists():
                    raw = json.loads(self.prev_path.read_text(encoding="utf-8"))
                    return clamp_params(raw).params
                raise
        params = Params()
        self.save(params)
        return params

    def save(self, params: Params) -> Params:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = params.model_dump(mode="json")
        self.tmp_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if self.path.exists():
            self.prev_path.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        self.tmp_path.replace(self.path)
        return params

    def replace(self, result: ClampResult) -> ClampResult:
        self.save(result.params)
        return result
