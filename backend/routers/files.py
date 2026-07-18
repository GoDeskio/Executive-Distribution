import uuid
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import Response
from bson import ObjectId

from core.db import db
from core.config import APP_NAME, MIME_TYPES
from core.security import require_perm
from core.utils import clean, now_iso
from core.audit import log_action
from storage import put_object, get_object

router = APIRouter(prefix="/api")


@router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form("asset"),
                      client_id: str = Form(""), user: dict = Depends(require_perm("storage"))):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "bin"
    path = f"{APP_NAME}/{category}/{uuid.uuid4()}.{ext}"
    data = await file.read()
    ctype = file.content_type or MIME_TYPES.get(ext, "application/octet-stream")
    result = put_object(path, data, ctype)
    doc = {
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": ctype,
        "size": result.get("size", len(data)),
        "category": category,
        "client_id": client_id or None,
        "is_deleted": False,
        "created_at": now_iso(),
    }
    res = await db.files.insert_one(doc)
    saved = await db.files.find_one({"_id": res.inserted_id})
    out = clean(saved)
    out["url"] = f"/api/files/{out['id']}/raw"
    return out


@router.get("/files")
async def list_files(category: str = None, user: dict = Depends(require_perm("storage"))):
    q = {"is_deleted": False}
    if category:
        q["category"] = category
    docs = await db.files.find(q).sort("created_at", -1).to_list(1000)
    out = []
    for d in docs:
        c = clean(d)
        c["url"] = f"/api/files/{c['id']}/raw"
        out.append(c)
    return out


@router.get("/files/{file_id}/raw")
async def serve_file(file_id: str):
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=404, detail="Not found")
    record = await db.files.find_one({"_id": ObjectId(file_id), "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    data, ctype = get_object(record["storage_path"])
    return Response(content=data, media_type=record.get("content_type", ctype))


@router.delete("/files/{file_id}")
async def delete_file(file_id: str, user: dict = Depends(require_perm("storage"))):
    await db.files.update_one({"_id": ObjectId(file_id)}, {"$set": {"is_deleted": True}})
    await log_action(user, "delete", "file", file_id)
    return {"ok": True}
