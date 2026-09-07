from common.storage import ObjectStore


def test_object_store_sha_and_soft_disable(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIO_ENABLED", "0")
    store = ObjectStore(endpoint="localhost:1")
    assert store.enabled is False or store.put_bytes(source_id="t", key_suffix="x", data=b"hi") is None
    assert store.sha256(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
