from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from core.db import db
from core.security import require_any_perm
from core.settings_store import get_settings_doc, resolve_base_url

router = APIRouter(prefix="/api")


def _sanitize_settings(doc: dict) -> dict:
    doc = dict(doc)
    doc.pop("_id", None)
    own = (doc.pop("ai_own_key", "") or "").strip()
    doc["has_own_key"] = bool(own)
    email_key = (doc.pop("email_api_key", "") or "").strip()
    doc["has_email_key"] = bool(email_key)
    slack = (doc.pop("slack_webhook_url", "") or "").strip()
    doc["has_slack_webhook"] = bool(slack)
    stytch = (doc.pop("stytch_secret", "") or "").strip()
    doc["has_stytch_secret"] = bool(stytch)
    return doc


@router.get("/settings")
async def get_settings():
    doc = await db.settings.find_one({"_id": "site"})
    if not doc:
        return {}
    return _sanitize_settings(doc)


@router.put("/settings")
async def update_settings(payload: dict, user: dict = Depends(require_any_perm("settings", "seo"))):
    payload.pop("_id", None)
    payload.pop("has_own_key", None)
    payload.pop("has_email_key", None)
    payload.pop("has_slack_webhook", None)
    payload.pop("has_stytch_secret", None)
    await db.settings.update_one({"_id": "site"}, {"$set": payload}, upsert=True)
    doc = await db.settings.find_one({"_id": "site"})
    return _sanitize_settings(doc)


@router.get("/sitemap.xml")
async def sitemap(request: Request):
    settings = await get_settings_doc()
    base = resolve_base_url(settings, request)
    services = await db.services.find({"published": True}).to_list(500)
    urls = [
        {"loc": f"{base}/", "priority": "1.0"},
        {"loc": f"{base}/#services", "priority": "0.8"},
        {"loc": f"{base}/#about", "priority": "0.6"},
        {"loc": f"{base}/#contact", "priority": "0.6"},
    ]
    for p in (settings.get("page_seo") or []):
        path = (p.get("path") or "").strip()
        if path and not any(u["loc"].endswith(path) for u in urls):
            urls.append({"loc": f"{base}/{path.lstrip('/')}", "priority": "0.7"})
    for sv in services:
        slug = sv.get("slug")
        if slug:
            urls.append({"loc": f"{base}/services/{slug}", "priority": "0.8"})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    items = "".join(
        f"<url><loc>{u['loc']}</loc><lastmod>{today}</lastmod>"
        f"<changefreq>weekly</changefreq><priority>{u['priority']}</priority></url>"
        for u in urls
    )
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f"{items}</urlset>")
    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt")
async def robots(request: Request):
    settings = await get_settings_doc()
    base = resolve_base_url(settings, request)
    txt = f"User-agent: *\nAllow: /\n\nSitemap: {base}/api/sitemap.xml\n"
    return Response(content=txt, media_type="text/plain")
