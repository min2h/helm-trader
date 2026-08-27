from __future__ import annotations

import threading
from pathlib import Path

from helm.actors.control_actor import ControlActor
from helm.config.store import ParamsStore


class ActorHub:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._lock = threading.Lock()
        self._actors: dict[int, ControlActor] = {}

    def for_user(self, user_id: int) -> ControlActor:
        with self._lock:
            actor = self._actors.get(user_id)
            if actor is None:
                path = self.data_dir / "users" / str(user_id) / "params.json"
                actor = ControlActor(ParamsStore(path))
                self._actors[user_id] = actor
            return actor
