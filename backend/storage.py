"""Portable object storage.

Two backends selectable via STORAGE_BACKEND env var:
  - "emergent" (default): Emergent object storage (works inside Emergent).
  - "local":  local filesystem (works anywhere, for self-hosting).

Public API: init_storage(), put_object(path, data, content_type), get_object(path)
"""
import os
import logging
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "emergent").lower()
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
LOCAL_DIR = Path(os.environ.get("LOCAL_STORAGE_DIR", str(Path(__file__).parent / "uploads")))

_storage_key = None


def init_storage():
    if STORAGE_BACKEND == "local":
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        return "local"
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    if STORAGE_BACKEND == "local":
        dest = LOCAL_DIR / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {"path": path, "size": len(data)}
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    if STORAGE_BACKEND == "local":
        src = LOCAL_DIR / path
        if not src.exists():
            raise FileNotFoundError(path)
        return src.read_bytes(), "application/octet-stream"
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
