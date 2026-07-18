import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from core.db import db
from core.security import require_superadmin
from core.settings_store import get_settings_doc
from core.updater import run_check, status_from_settings
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
    """Runs a self-host update script if configured via the UPDATE_SCRIPT env var.
    On managed hosting (no script), returns guidance to use the platform Deploy."""
    settings = await get_settings_doc()
    script = os.environ.get("UPDATE_SCRIPT", "").strip()
    if not script or not os.path.exists(script):
        return {
            "ok": False,
            "managed": True,
            "message": ("Automatic apply isn't available in this hosting environment. "
                        "Use your platform's Deploy to publish the new version. "
                        "For self-hosting, set the UPDATE_SCRIPT env var to your update script "
                        "(see deploy/update.sh) and this button will run it."),
        }
    import asyncio
    async def _run():
        try:
            proc = await asyncio.create_subprocess_exec(
                "/bin/bash", script,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            out, _ = await proc.communicate()
            ok = proc.returncode == 0
            latest = (settings.get("update_latest_version") or "").strip()
            update = {"update_last_apply": now_iso(),
                      "update_last_apply_ok": ok,
                      "update_last_apply_log": (out or b"").decode(errors="ignore")[-2000:]}
            if ok and latest:
                update["update_current_version"] = latest
                update["update_available"] = False
            await db.settings.update_one({"_id": "site"}, {"$set": update})
        except Exception as e:
            await db.settings.update_one({"_id": "site"},
                                         {"$set": {"update_last_apply_ok": False, "update_last_apply_log": str(e)[:500]}})
    asyncio.create_task(_run())
    await log_action(user, "generate", "settings", detail="triggered self-host update script")
    return {"ok": True, "managed": False, "message": "Update script started. Services may restart shortly."}
