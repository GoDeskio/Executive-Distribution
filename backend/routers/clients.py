import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from core.db import db
from core.security import require_perm
from core.utils import clean, now_iso

router = APIRouter(prefix="/api")


class ClientInput(BaseModel):
    name: str
    company: str = ""
    email: str = ""
    phone: str = ""
    status: str = "lead"
    value: float = 0
    tags: List[str] = []
    notes: str = ""


class PortalTokenInput(BaseModel):
    expires_days: Optional[int] = None


@router.get("/clients")
async def list_clients(user: dict = Depends(require_perm("crm"))):
    docs = await db.clients.find({}).sort("created_at", -1).to_list(1000)
    return [clean(d) for d in docs]


@router.post("/clients")
async def create_client(data: ClientInput, user: dict = Depends(require_perm("crm"))):
    doc = data.model_dump()
    doc["created_at"] = now_iso()
    res = await db.clients.insert_one(doc)
    return clean(await db.clients.find_one({"_id": res.inserted_id}))


@router.put("/clients/{client_id}")
async def update_client(client_id: str, data: ClientInput, user: dict = Depends(require_perm("crm"))):
    await db.clients.update_one({"_id": ObjectId(client_id)}, {"$set": data.model_dump()})
    return clean(await db.clients.find_one({"_id": ObjectId(client_id)}))


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, user: dict = Depends(require_perm("crm"))):
    await db.clients.delete_one({"_id": ObjectId(client_id)})
    return {"ok": True}


@router.get("/clients/{client_id}/documents")
async def client_documents(client_id: str, user: dict = Depends(require_perm("crm"))):
    docs = await db.documents.find({"client_id": client_id}).sort("created_at", -1).to_list(500)
    return [clean(d) for d in docs]


@router.post("/clients/{client_id}/portal-token")
async def generate_portal_token(client_id: str, data: PortalTokenInput = PortalTokenInput(),
                                user: dict = Depends(require_perm("crm"))):
    token = secrets.token_urlsafe(16)
    updates = {"portal_token": token, "portal_expires_at": None}
    if data and data.expires_days:
        updates["portal_expires_at"] = (datetime.now(timezone.utc) + timedelta(days=int(data.expires_days))).isoformat()
    res = await db.clients.update_one({"_id": ObjectId(client_id)}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"token": token, "expires_at": updates["portal_expires_at"]}


@router.delete("/clients/{client_id}/portal-token")
async def revoke_portal_token(client_id: str, user: dict = Depends(require_perm("crm"))):
    await db.clients.update_one({"_id": ObjectId(client_id)}, {"$unset": {"portal_token": ""}})
    return {"ok": True}
