from helm.auth.crypto import SecretBox, new_master_key


def test_roundtrip(tmp_path) -> None:
    box = SecretBox(new_master_key(), tmp_path / "key")
    token = box.encrypt("sk-live")
    assert token != "sk-live"
    assert box.decrypt(token) == "sk-live"
