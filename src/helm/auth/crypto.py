from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


class SecretBox:
    def __init__(self, key: str = "", persist_path: Path | None = None) -> None:
        fernet: Fernet | None = None
        if key:
            try:
                fernet = Fernet(key.encode("utf-8"))
            except ValueError:
                fernet = None
        if fernet is None and persist_path and persist_path.exists():
            fernet = Fernet(persist_path.read_bytes().strip())
        if fernet is None:
            generated = Fernet.generate_key()
            if persist_path:
                persist_path.parent.mkdir(parents=True, exist_ok=True)
                persist_path.write_bytes(generated)
            fernet = Fernet(generated)
        self._fernet = fernet

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("cannot decrypt secret") from exc


def new_master_key() -> str:
    return Fernet.generate_key().decode("ascii")
