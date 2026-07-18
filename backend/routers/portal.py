import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
from bson import ObjectId

from core.db import db
from core.utils import clean, now_iso, logger
from core.settings_store import get_settings_doc

router = APIRouter(prefix="/api")


class PortalApproveInput(BaseModel):
    document_id: str


def _portal_expired(client: dict) -> bool:
    exp = client.get("portal_expires_at")
    if not exp:
        return False
    try:
        return datetime.now(timezone.utc) > datetime.fromisoformat(exp)
    except Exception:
        return False


def _send_approval_alerts(settings: dict, client_name: str, doc_number: str, amount):
    """Best-effort Slack alert when a client approves a quote."""
    if not settings.get("alert_on_approval"):
        return
    webhook = (settings.get("slack_webhook_url") or "").strip()
    if webhook.startswith("http"):
        try:
            text = (f":white_check_mark: *Quote approved* — {client_name} approved "
                    f"{doc_number} (${float(amount or 0):,.2f}) on the client portal.")
            requests.post(webhook, json={"text": text}, timeout=8)
        except Exception as e:
            logger.warning(f"Slack alert failed: {e}")


@router.get("/portal/{token}")
async def client_portal(token: str):
    client = await db.clients.find_one({"portal_token": token})
    if not client or _portal_expired(client):
        raise HTTPException(status_code=404, detail="Portal not found")
    settings = await get_settings_doc()
    cid = str(client["_id"])
    docs = await db.documents.find({"client_id": cid, "pdf_file_id": {"$ne": None}, "shared": {"$ne": False}}).sort("created_at", -1).to_list(500)
    documents = [{
        "id": str(d["_id"]),
        "number": d.get("number"), "doc_type": d.get("doc_type"), "date": d.get("date"),
        "grand_total": d.get("grand_total", 0), "port": d.get("port", ""),
        "destination": d.get("destination", ""), "status": d.get("status", "generated"),
        "download_url": f"/api/files/{d['pdf_file_id']}/raw",
    } for d in docs]
    return {
        "client": {"name": client.get("name", ""), "company": client.get("company", "")},
        "company": {
            "name": settings.get("company_name", "Executive Distribution"),
            "logo_url": settings.get("logo_url", ""),
            "tagline": settings.get("tagline", ""),
            "contact_email": settings.get("contact_email", ""),
            "phone": settings.get("phone", ""),
        },
        "documents": documents,
    }


@router.post("/portal/{token}/approve")
async def portal_approve(token: str, data: PortalApproveInput):
    client = await db.clients.find_one({"portal_token": token})
    if not client or _portal_expired(client):
        raise HTTPException(status_code=404, detail="Portal not found")
    doc = await db.documents.find_one({"_id": ObjectId(data.document_id), "client_id": str(client["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.documents.update_one({"_id": doc["_id"]}, {"$set": {"status": "approved", "approved_at": now_iso()}})
    await db.notifications.insert_one({
        "type": "quote_approved", "client_name": client.get("name", ""),
        "document_number": doc.get("number", ""), "document_id": str(doc["_id"]),
        "read": False, "created_at": now_iso(),
    })
    settings = await get_settings_doc()
    asyncio.create_task(asyncio.to_thread(
        _send_approval_alerts, settings, client.get("name", ""), doc.get("number", ""), doc.get("grand_total", 0)
    ))
    return {"ok": True, "status": "approved"}
