import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from core.db import db
from core.security import require_perm
from core.utils import clean, now_iso
from core.audit import log_action

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
    await log_action(user, "create", "client", str(res.inserted_id), data.name)
    return clean(await db.clients.find_one({"_id": res.inserted_id}))


@router.put("/clients/{client_id}")
async def update_client(client_id: str, data: ClientInput, user: dict = Depends(require_perm("crm"))):
    await db.clients.update_one({"_id": ObjectId(client_id)}, {"$set": data.model_dump()})
    await log_action(user, "update", "client", client_id, data.name)
    return clean(await db.clients.find_one({"_id": ObjectId(client_id)}))


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, user: dict = Depends(require_perm("crm"))):
    target = await db.clients.find_one({"_id": ObjectId(client_id)})
    await db.clients.delete_one({"_id": ObjectId(client_id)})
    await log_action(user, "delete", "client", client_id, (target or {}).get("name", ""))
    return {"ok": True}


class BulkUpdateInput(BaseModel):
    ids: List[str]
    status: Optional[str] = None
    add_tag: Optional[str] = None


@router.post("/clients/bulk")
async def bulk_update_clients(data: BulkUpdateInput, user: dict = Depends(require_perm("crm"))):
    oids = [ObjectId(i) for i in data.ids if ObjectId.is_valid(i)]
    if not oids:
        raise HTTPException(status_code=400, detail="No valid client ids provided")
    updated = 0
    if data.status:
        res = await db.clients.update_many({"_id": {"$in": oids}}, {"$set": {"status": data.status}})
        updated = res.modified_count
    tag = (data.add_tag or "").strip()
    if tag:
        res = await db.clients.update_many({"_id": {"$in": oids}}, {"$addToSet": {"tags": tag}})
        updated = max(updated, res.modified_count)
    await log_action(user, "update", "client", detail=f"bulk: {len(oids)} client(s), status={data.status}, tag={tag}")
    return {"ok": True, "matched": len(oids), "updated": updated}


class BulkDeleteInput(BaseModel):
    ids: List[str]


@router.post("/clients/bulk-delete")
async def bulk_delete_clients(data: BulkDeleteInput, user: dict = Depends(require_perm("crm"))):
    oids = [ObjectId(i) for i in data.ids if ObjectId.is_valid(i)]
    if not oids:
        raise HTTPException(status_code=400, detail="No valid client ids provided")
    res = await db.clients.delete_many({"_id": {"$in": oids}})
    await log_action(user, "delete", "client", detail=f"bulk delete: {res.deleted_count} client(s)")
    return {"ok": True, "deleted": res.deleted_count}


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
