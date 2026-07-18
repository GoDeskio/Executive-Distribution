from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from bson import ObjectId

from core.db import db
from core.config import ALL_PERMS
from core.security import require_superadmin, hash_password
from core.utils import clean, now_iso
from core.audit import log_action

router = APIRouter(prefix="/api")


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str = ""
    permissions: List[str] = []


class UserManageUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[List[str]] = None
    active: Optional[bool] = None


class UserPassword(BaseModel):
    password: str


@router.get("/users")
async def list_users(user: dict = Depends(require_superadmin)):
    docs = await db.users.find({}).sort("created_at", 1).to_list(200)
    return [clean(d) for d in docs]


@router.get("/permissions")
async def list_permissions(user: dict = Depends(require_superadmin)):
    return {"permissions": ALL_PERMS}


@router.post("/users")
async def create_user(data: UserCreate, user: dict = Depends(require_superadmin)):
    email = data.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="A user with this email already exists")
    perms = [p for p in data.permissions if p in ALL_PERMS]
    doc = {"email": email, "password_hash": hash_password(data.password), "name": data.name or email.split("@")[0],
           "role": "subadmin", "permissions": perms, "active": True, "avatar_url": "", "created_at": now_iso()}
    res = await db.users.insert_one(doc)
    created = await db.users.find_one({"_id": res.inserted_id})
    await log_action(user, "create", "user", str(res.inserted_id), email)
    return clean(created)


@router.put("/users/{user_id}")
async def update_user(user_id: str, data: UserManageUpdate, user: dict = Depends(require_superadmin)):
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("role") == "superadmin":
        raise HTTPException(status_code=400, detail="Cannot modify a super admin account here")
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.permissions is not None:
        updates["permissions"] = [p for p in data.permissions if p in ALL_PERMS]
    if data.active is not None:
        updates["active"] = data.active
    if updates:
        await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
    await log_action(user, "update", "user", user_id, target.get("email", ""))
    return clean(await db.users.find_one({"_id": ObjectId(user_id)}))


@router.post("/users/{user_id}/password")
async def reset_user_password(user_id: str, data: UserPassword, user: dict = Depends(require_superadmin)):
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target or target.get("role") == "superadmin":
        raise HTTPException(status_code=400, detail="Cannot reset this account's password")
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"password_hash": hash_password(data.password)}})
    await log_action(user, "password", "user", user_id, target.get("email", ""))
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_superadmin)):
    target = await db.users.find_one({"_id": ObjectId(user_id)})
    if not target:
        return {"ok": True}
    if target.get("role") == "superadmin":
        raise HTTPException(status_code=400, detail="Cannot remove a super admin")
    await db.users.delete_one({"_id": ObjectId(user_id)})
    await log_action(user, "delete", "user", user_id, target.get("email", ""))
    return {"ok": True}
