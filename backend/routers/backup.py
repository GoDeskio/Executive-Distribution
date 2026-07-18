from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse

from core.security import require_superadmin
from core.settings_store import get_settings_doc
from core.audit import log_action
from core.backup import (create_backup, save_backup_to_disk, list_disk_backups,
                         read_disk_backup, delete_disk_backup, restore_backup,
                         resolve_backup_dir)

router = APIRouter(prefix="/api")


@router.get("/backup/config")
async def backup_config(user: dict = Depends(require_superadmin)):
    s = await get_settings_doc()
    return {
        "backup_dir": s.get("backup_dir") or "",
        "effective_dir": resolve_backup_dir(s),
        "backup_include_files": bool(s.get("backup_include_files", True)),
        "backup_auto_before_update": bool(s.get("backup_auto_before_update", True)),
        "server_backups": list_disk_backups(s),
    }


@router.get("/backup/download")
async def backup_download(include_files: bool = True, user: dict = Depends(require_superadmin)):
    content, filename = await create_backup(include_files)
    await log_action(user, "generate", "settings", detail=f"downloaded backup ({filename})")
    return StreamingResponse(iter([content]), media_type="application/zip",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post("/backup/save")
async def backup_save(user: dict = Depends(require_superadmin)):
    s = await get_settings_doc()
    try:
        result = await save_backup_to_disk(s, bool(s.get("backup_include_files", True)))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not write backup: {str(e)[:200]}")
    await log_action(user, "generate", "settings", detail=f"saved backup to server ({result['filename']})")
    return {"ok": True, **result}


@router.get("/backup/server/{filename}")
async def backup_server_download(filename: str, user: dict = Depends(require_superadmin)):
    s = await get_settings_doc()
    try:
        content = read_disk_backup(s, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup not found")
    return StreamingResponse(iter([content]), media_type="application/zip",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.delete("/backup/server/{filename}")
async def backup_server_delete(filename: str, user: dict = Depends(require_superadmin)):
    s = await get_settings_doc()
    ok = delete_disk_backup(s, filename)
    if ok:
        await log_action(user, "delete", "settings", detail=f"deleted backup ({filename})")
    return {"ok": ok}


@router.post("/backup/restore")
async def backup_restore(file: UploadFile = File(...), user: dict = Depends(require_superadmin)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        restored = await restore_backup(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Restore failed: {str(e)[:200]}")
    await log_action(user, "update", "settings", detail=f"restored backup: {restored}")
    return {"ok": True, "restored": restored}
