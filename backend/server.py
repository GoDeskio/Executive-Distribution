import os
import asyncio
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# core/__init__.py loads the .env file on import
from core.db import client, db
from core.config import ALL_PERMS
from core.utils import now_iso, slugify, logger
from core.security import hash_password, verify_password
from core.settings_store import DEFAULT_SERVICES, DEFAULT_SETTINGS, get_settings_doc
from core.updater import run_check, run_update_script
from storage import init_storage

from routers import (auth, users, services, settings, clients, portal,
                     notifications, quotes, files, analytics, chat, documents, search, audit, updates, backup)

app = FastAPI()

for module in (auth, users, services, settings, clients, portal, notifications,
               quotes, files, analytics, chat, documents, search, audit, updates, backup):
    app.include_router(module.router)


@app.on_event("startup")
async def startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.services.create_index("slug", unique=True)
        await db.visitors.create_index("session_id", unique=True)
        await db.events.create_index([("path", 1), ("event_type", 1)])
    except Exception as e:
        logger.warning(f"Index warning: {e}")

    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_password = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_password),
                                   "name": "Executive Admin", "role": "superadmin", "permissions": ALL_PERMS,
                                   "active": True, "avatar_url": "", "created_at": now_iso()})
        logger.info("Seeded superadmin user")
    else:
        # Non-destructive repair only. NEVER overwrite an existing admin's password
        # or any other user/site data — chosen credentials must persist across
        # restarts and auto-updates.
        updates = {}
        if existing.get("role") != "superadmin":
            updates["role"] = "superadmin"
        if not existing.get("permissions"):
            updates["permissions"] = ALL_PERMS
        if existing.get("active") is None:
            updates["active"] = True
        if updates:
            await db.users.update_one({"email": admin_email}, {"$set": updates})

    if await db.services.count_documents({}) == 0:
        for i, s in enumerate(DEFAULT_SERVICES):
            s = dict(s)
            s.update({"slug": slugify(s["title"]), "order": i, "published": True,
                      "sections": [], "meta_title": s["title"], "meta_description": s["short_description"],
                      "keywords": "", "created_at": now_iso(), "updated_at": now_iso()})
            await db.services.insert_one(s)
        logger.info("Seeded default services")

    if not await db.settings.find_one({"_id": "site"}):
        doc = dict(DEFAULT_SETTINGS)
        doc["_id"] = "site"
        await db.settings.insert_one(doc)
        logger.info("Seeded site settings")

    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")

    app.state.update_poller = asyncio.create_task(_update_poller())
    app.state.backup_poller = asyncio.create_task(_backup_poller())


# Interval between automatic update checks (seconds). Default: 24h.
UPDATE_CHECK_INTERVAL = int(os.environ.get("UPDATE_CHECK_INTERVAL_SECONDS", 86400))
UPDATE_CHECK_INITIAL_DELAY = 90  # let the app settle before the first check


async def _update_poller():
    """Periodically checks GitHub for a new version so the 'Update available'
    banner surfaces on its own — no admin needs to open the dashboard. Pull/notify
    only; auto-apply runs only when explicitly enabled AND a self-host script exists."""
    await asyncio.sleep(UPDATE_CHECK_INITIAL_DELAY)
    while True:
        try:
            s = await get_settings_doc()
            if (s.get("update_repo_url") or "").strip() and s.get("update_auto_check", True):
                result = await run_check(s)
                if result.get("update_available"):
                    logger.info(f"Update available: {result.get('update_latest_version')}")
                    if s.get("update_auto_apply") and os.environ.get("UPDATE_SCRIPT"):
                        fresh = await get_settings_doc()
                        await run_update_script(fresh)
        except Exception as e:
            logger.warning(f"update poller error: {e}")
        await asyncio.sleep(UPDATE_CHECK_INTERVAL)


async def _backup_poller():
    """Scheduled automatic backups to the server folder, pruned to the retention count."""
    await asyncio.sleep(120)
    while True:
        interval_hours = 24
        try:
            s = await get_settings_doc()
            interval_hours = int(s.get("backup_schedule_interval_hours", 24) or 24)
            if s.get("backup_schedule_enabled"):
                last = s.get("backup_last_scheduled_at")
                due = True
                if last:
                    try:
                        from datetime import datetime, timezone
                        due = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() >= interval_hours * 3600 - 60
                    except Exception:
                        due = True
                if due:
                    from core.backup import save_backup_to_disk, prune_disk_backups
                    info = await save_backup_to_disk(s, bool(s.get("backup_include_files", True)))
                    removed = prune_disk_backups(s, s.get("backup_retention", 7))
                    await db.settings.update_one({"_id": "site"},
                                                 {"$set": {"backup_last_scheduled_at": now_iso(),
                                                           "backup_last_scheduled_file": info.get("filename")}})
                    logger.info(f"scheduled backup saved: {info.get('filename')} (pruned {len(removed)})")
        except Exception as e:
            logger.warning(f"backup poller error: {e}")
        await asyncio.sleep(max(1, min(interval_hours, 24)) * 3600)


@app.on_event("shutdown")
async def shutdown_db_client():
    for attr in ("update_poller", "backup_poller"):
        task = getattr(app.state, attr, None)
        if task:
            task.cancel()
    client.close()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
