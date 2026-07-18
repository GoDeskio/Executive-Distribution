import os
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# core/__init__.py loads the .env file on import
from core.db import client, db
from core.config import ALL_PERMS
from core.utils import now_iso, slugify, logger
from core.security import hash_password, verify_password
from core.settings_store import DEFAULT_SERVICES, DEFAULT_SETTINGS
from storage import init_storage

from routers import (auth, users, services, settings, clients, portal,
                     notifications, quotes, files, analytics, chat, documents, search, audit)

app = FastAPI()

for module in (auth, users, services, settings, clients, portal, notifications,
               quotes, files, analytics, chat, documents, search, audit):
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
        updates = {}
        if existing.get("role") != "superadmin":
            updates["role"] = "superadmin"
        if not existing.get("permissions"):
            updates["permissions"] = ALL_PERMS
        if existing.get("active") is None:
            updates["active"] = True
        if not verify_password(admin_password, existing["password_hash"]):
            updates["password_hash"] = hash_password(admin_password)
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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
