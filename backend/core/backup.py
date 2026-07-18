import io
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from bson import json_util

from core.db import db
from core.utils import now_iso, logger
from storage import put_object, get_object

# Collections included in a backup. Analytics (events/visitors) are intentionally
# excluded to keep backups lean; core business + auth + audit data is preserved.
BACKUP_COLLECTIONS = ["users", "services", "settings", "clients", "quotes",
                      "documents", "files", "notifications", "audit_logs"]

DEFAULT_BACKUP_DIR = os.environ.get("BACKUP_DIR", str(Path(__file__).parent.parent / "backups"))


def resolve_backup_dir(settings: dict) -> str:
    d = (settings.get("backup_dir") or "").strip() or DEFAULT_BACKUP_DIR
    return d


async def create_backup(include_files: bool = True) -> tuple[bytes, str]:
    """Builds an in-memory zip: data.json (all collections) + objects/ (uploaded files)."""
    data = {"created_at": now_iso(), "app": "executive-distribution", "collections": {}}
    file_docs = []
    for name in BACKUP_COLLECTIONS:
        docs = await db[name].find({}).to_list(100000)
        data["collections"][name] = docs
        if name == "files":
            file_docs = docs

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("data.json", json_util.dumps(data, indent=2))
        manifest = {"include_files": include_files, "object_count": 0}
        if include_files:
            count = 0
            for fd in file_docs:
                if fd.get("is_deleted"):
                    continue
                sp = fd.get("storage_path")
                if not sp:
                    continue
                try:
                    content, _ = get_object(sp)
                    zf.writestr(f"objects/{sp}", content)
                    count += 1
                except Exception as e:
                    logger.warning(f"backup: could not read object {sp}: {e}")
            manifest["object_count"] = count
        zf.writestr("manifest.json", json_util.dumps(manifest))

    buf.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return buf.getvalue(), f"exd-backup-{ts}.zip"


async def save_backup_to_disk(settings: dict, include_files: bool = True) -> dict:
    dir_path = resolve_backup_dir(settings)
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    content, filename = await create_backup(include_files)
    dest = Path(dir_path) / filename
    dest.write_bytes(content)
    return {"filename": filename, "path": str(dest), "size": len(content), "created_at": now_iso()}


def list_disk_backups(settings: dict) -> list:
    dir_path = Path(resolve_backup_dir(settings))
    if not dir_path.exists():
        return []
    out = []
    for f in sorted(dir_path.glob("exd-backup-*.zip"), reverse=True):
        st = f.stat()
        out.append({"filename": f.name, "size": st.st_size,
                    "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()})
    return out


def read_disk_backup(settings: dict, filename: str) -> bytes:
    # prevent path traversal — only allow plain backup filenames
    if "/" in filename or ".." in filename or not filename.startswith("exd-backup-"):
        raise FileNotFoundError(filename)
    path = Path(resolve_backup_dir(settings)) / filename
    if not path.exists():
        raise FileNotFoundError(filename)
    return path.read_bytes()


def delete_disk_backup(settings: dict, filename: str) -> bool:
    if "/" in filename or ".." in filename or not filename.startswith("exd-backup-"):
        return False
    path = Path(resolve_backup_dir(settings)) / filename
    if path.exists():
        path.unlink()
        return True
    return False


def prune_disk_backups(settings: dict, keep: int) -> list:
    """Keeps the newest `keep` backups in the folder; deletes older ones. Returns removed names."""
    keep = max(int(keep or 1), 1)
    dir_path = Path(resolve_backup_dir(settings))
    if not dir_path.exists():
        return []
    files = sorted(dir_path.glob("exd-backup-*.zip"), key=lambda f: f.stat().st_mtime, reverse=True)
    removed = []
    for f in files[keep:]:
        try:
            f.unlink()
            removed.append(f.name)
        except Exception as e:
            logger.warning(f"prune: could not delete {f.name}: {e}")
    return removed


async def restore_backup(zip_bytes: bytes) -> dict:
    """DESTRUCTIVE but safe: snapshots current data first and rolls back on any failure."""
    buf = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(buf, "r") as zf:
        raw = zf.read("data.json").decode("utf-8")
        data = json_util.loads(raw)
        collections = {k: v for k, v in data.get("collections", {}).items() if k in BACKUP_COLLECTIONS}

        # Snapshot current state so we can roll back if an insert fails midway.
        snapshot = {}
        for name in collections:
            snapshot[name] = await db[name].find({}).to_list(100000)

        restored = {}
        try:
            for name, docs in collections.items():
                await db[name].delete_many({})
                if docs:
                    await db[name].insert_many(docs)
                restored[name] = len(docs)
        except Exception as e:
            logger.error(f"restore failed ({e}) — rolling back to pre-restore state")
            for name, docs in snapshot.items():
                try:
                    await db[name].delete_many({})
                    if docs:
                        await db[name].insert_many(docs)
                except Exception as re:
                    logger.error(f"rollback error on {name}: {re}")
            raise RuntimeError(f"Restore aborted and rolled back: {str(e)[:150]}")

        # Restore object files (non-fatal; data already committed)
        obj_count = 0
        for member in zf.namelist():
            if member.startswith("objects/") and not member.endswith("/"):
                sp = member[len("objects/"):]
                try:
                    put_object(sp, zf.read(member), "application/octet-stream")
                    obj_count += 1
                except Exception as e:
                    logger.warning(f"restore: could not write object {sp}: {e}")
        restored["_objects"] = obj_count
    return restored
