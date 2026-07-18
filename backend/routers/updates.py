import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from core.db import db
from core.security import require_superadmin
from core.settings_store import get_settings_doc
from core.updater import run_check, status_from_settings, run_update_script
from core.audit import log_action
from core.utils import now_iso

router = APIRouter(prefix="/api")

STALE_MINUTES = 60


@router.get("/updates/status")
async def updates_status(user: dict = Depends(require_superadmin)):
    settings = await get_settings_doc()
    # Auto-refresh if enabled and the cached check is stale or missing.
    if (settings.get("update_repo_url") or "").strip() and settings.get("update_auto_check", True):
        last = settings.get("update_last_checked")
        stale = True
        if last:
            try:
                stale = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() > STALE_MINUTES * 60
            except Exception:
                stale = True
        if stale:
            await run_check(settings)
            settings = await get_settings_doc()
    return status_from_settings(settings)


@router.post("/updates/check")
async def updates_check(user: dict = Depends(require_superadmin)):
    settings = await get_settings_doc()
    result = await run_check(settings)
    await log_action(user, "generate", "settings", detail="checked for updates")
    return result


@router.post("/updates/mark-current")
async def updates_mark_current(user: dict = Depends(require_superadmin)):
    """Baseline: record the latest known version as the currently-deployed one."""
    settings = await get_settings_doc()
    latest = (settings.get("update_latest_version") or "").strip()
    if not latest:
        return {"ok": False, "error": "No latest version known yet — run a check first."}
    await db.settings.update_one({"_id": "site"},
                                 {"$set": {"update_current_version": latest, "update_available": False}})
    await log_action(user, "update", "settings", detail=f"marked current version {latest}")
    return {"ok": True, "current_version": latest}


@router.post("/updates/apply")
async def updates_apply(user: dict = Depends(require_superadmin)):
    """Runs a self-host update script if UPDATE_SCRIPT is configured; on managed
    hosting returns guidance to use the platform Deploy."""
    settings = await get_settings_doc()
    result = await run_update_script(settings)
    if result.get("ok"):
        await log_action(user, "generate", "settings", detail="triggered self-host update script")
    return result
