from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from bson import ObjectId

from core.db import db
from core.security import require_perm
from core.utils import clean, now_iso, slugify
from core.audit import log_action
from core.seo_ping import maybe_autoping

router = APIRouter(prefix="/api")


class ServiceInput(BaseModel):
    title: str
    short_description: str = ""
    full_description: str = ""
    image_url: str = ""
    icon: str = "package"
    order: int = 0
    published: bool = True
    features: List[str] = []
    sections: List[dict] = []
    meta_title: str = ""
    meta_description: str = ""
    keywords: str = ""


@router.get("/services")
async def list_services(all: bool = False, user_check: bool = False):
    q = {} if all else {"published": True}
    docs = await db.services.find(q).sort("order", 1).to_list(500)
    return [clean(d) for d in docs]


@router.get("/services/{slug}")
async def get_service(slug: str):
    doc = await db.services.find_one({"slug": slug})
    if not doc:
        doc = await db.services.find_one({"_id": ObjectId(slug)}) if ObjectId.is_valid(slug) else None
    if not doc:
        raise HTTPException(status_code=404, detail="Service not found")
    return clean(doc)


@router.post("/services")
async def create_service(data: ServiceInput, user: dict = Depends(require_perm("services"))):
    doc = data.model_dump()
    base = slugify(data.title)
    slug = base
    i = 1
    while await db.services.find_one({"slug": slug}):
        slug = f"{base}-{i}"
        i += 1
    doc["slug"] = slug
    doc["created_at"] = now_iso()
    doc["updated_at"] = now_iso()
    res = await db.services.insert_one(doc)
    await log_action(user, "create", "service", str(res.inserted_id), data.title)
    await maybe_autoping()
    return clean(await db.services.find_one({"_id": res.inserted_id}))


@router.put("/services/{service_id}")
async def update_service(service_id: str, data: ServiceInput, user: dict = Depends(require_perm("services"))):
    doc = data.model_dump()
    doc["updated_at"] = now_iso()
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": doc})
    await log_action(user, "update", "service", service_id, data.title)
    await maybe_autoping()
    return clean(await db.services.find_one({"_id": ObjectId(service_id)}))


@router.delete("/services/{service_id}")
async def delete_service(service_id: str, user: dict = Depends(require_perm("services"))):
    target = await db.services.find_one({"_id": ObjectId(service_id)})
    await db.services.delete_one({"_id": ObjectId(service_id)})
    await log_action(user, "delete", "service", service_id, (target or {}).get("title", ""))
    await maybe_autoping()
    return {"ok": True}
