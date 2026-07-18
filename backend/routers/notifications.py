from fastapi import APIRouter, Depends

from core.db import db
from core.security import get_current_user
from core.utils import clean

router = APIRouter(prefix="/api")


@router.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    docs = await db.notifications.find({}).sort("created_at", -1).to_list(50)
    return [clean(d) for d in docs]


@router.get("/notifications/unread-count")
async def unread_count(user: dict = Depends(get_current_user)):
    return {"count": await db.notifications.count_documents({"read": False})}


@router.post("/notifications/read")
async def mark_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"read": False}, {"$set": {"read": True}})
    return {"ok": True}
