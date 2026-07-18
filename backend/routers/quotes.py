import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from core.db import db
from core.config import APP_NAME, MIME_TYPES
from core.security import require_perm
from core.utils import clean, now_iso
from storage import put_object

router = APIRouter(prefix="/api")


def _store_upload(data: bytes, filename: str, content_type: str, category: str):
    ext = filename.split(".")[-1].lower() if "." in filename else "bin"
    path = f"{APP_NAME}/{category}/{uuid.uuid4()}.{ext}"
    ctype = content_type or MIME_TYPES.get(ext, "application/octet-stream")
    result = put_object(path, data, ctype)
    return result["path"], ctype, result.get("size", len(data))


class QuoteUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@router.post("/quotes")
async def create_quote(
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(""),
    phone: str = Form(""),
    destination: str = Form(""),
    description: str = Form(""),
    images: List[UploadFile] = File(default=[]),
):
    image_urls = []
    for img in images or []:
        if not img or not img.filename:
            continue
        data = await img.read()
        if not data:
            continue
        storage_path, ctype, size = _store_upload(data, img.filename, img.content_type, "quote")
        rec = {
            "storage_path": storage_path, "original_filename": img.filename,
            "content_type": ctype, "size": size, "category": "quote",
            "client_id": None, "is_deleted": False, "created_at": now_iso(),
        }
        res = await db.files.insert_one(rec)
        image_urls.append(f"/api/files/{str(res.inserted_id)}/raw")

    doc = {
        "name": name, "email": email, "company": company, "phone": phone,
        "destination": destination, "description": description,
        "images": image_urls, "status": "new", "notes": "", "created_at": now_iso(),
    }
    r = await db.quotes.insert_one(doc)
    return {"ok": True, "id": str(r.inserted_id)}


@router.get("/quotes")
async def list_quotes(user: dict = Depends(require_perm("crm"))):
    docs = await db.quotes.find({}).sort("created_at", -1).to_list(1000)
    return [clean(d) for d in docs]


@router.put("/quotes/{quote_id}")
async def update_quote(quote_id: str, data: QuoteUpdate, user: dict = Depends(require_perm("crm"))):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.quotes.update_one({"_id": ObjectId(quote_id)}, {"$set": updates})
    return clean(await db.quotes.find_one({"_id": ObjectId(quote_id)}))


@router.delete("/quotes/{quote_id}")
async def delete_quote(quote_id: str, user: dict = Depends(require_perm("crm"))):
    await db.quotes.delete_one({"_id": ObjectId(quote_id)})
    return {"ok": True}
