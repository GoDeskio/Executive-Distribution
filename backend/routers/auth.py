from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from core.db import db
from core.security import (verify_password, hash_password, create_access_token,
                           get_current_user)
from core.utils import clean
from core.settings_store import get_settings_doc
from core.audit import log_action

router = APIRouter(prefix="/api")


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


async def _lockout_config():
    s = await get_settings_doc()
    try:
        max_attempts = int(s.get("lockout_max_attempts", 5) or 5)
    except (TypeError, ValueError):
        max_attempts = 5
    try:
        lock_minutes = int(s.get("lockout_minutes", 15) or 15)
    except (TypeError, ValueError):
        lock_minutes = 15
    return max(1, max_attempts), max(1, lock_minutes)


@router.post("/auth/login")
async def login(data: LoginInput):
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    max_attempts, lock_minutes = await _lockout_config()
    now = datetime.now(timezone.utc)

    # If account is currently locked, reject early
    if user and user.get("locked_until"):
        try:
            lu = datetime.fromisoformat(user["locked_until"])
        except (TypeError, ValueError):
            lu = None
        if lu and lu > now:
            mins = max(1, int((lu - now).total_seconds() // 60) + 1)
            raise HTTPException(status_code=429,
                                detail=f"Account locked due to too many failed attempts. Try again in {mins} minute(s).")

    if not user or not verify_password(data.password, user["password_hash"]):
        if user:
            attempts = int(user.get("failed_attempts", 0) or 0) + 1
            if attempts >= max_attempts:
                locked_until = (now + timedelta(minutes=lock_minutes)).isoformat()
                await db.users.update_one({"_id": user["_id"]},
                                          {"$set": {"failed_attempts": 0, "locked_until": locked_until}})
                raise HTTPException(status_code=429,
                                    detail=f"Too many failed attempts. Account locked for {lock_minutes} minute(s).")
            await db.users.update_one({"_id": user["_id"]}, {"$set": {"failed_attempts": attempts}})
            remaining = max_attempts - attempts
            raise HTTPException(status_code=401,
                                detail=f"Invalid email or password. {remaining} attempt(s) remaining before lockout.")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Successful login — reset any counters/locks
    if user.get("failed_attempts") or user.get("locked_until"):
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"failed_attempts": 0, "locked_until": None}})
    token = create_access_token(str(user["_id"]), email)
    await log_action({"id": str(user["_id"]), "email": email, "name": user.get("name")},
                     "login", "auth")
    return {"token": token, "user": clean(user)}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"ok": True}


@router.put("/auth/profile")
async def update_profile(data: ProfileUpdate, user: dict = Depends(get_current_user)):
    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.avatar_url is not None:
        updates["avatar_url"] = data.avatar_url
    if data.new_password:
        full = await db.users.find_one({"_id": ObjectId(user["id"])})
        if not data.current_password or not verify_password(data.current_password, full["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        updates["password_hash"] = hash_password(data.new_password)
    if updates:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": updates})
    updated = await db.users.find_one({"_id": ObjectId(user["id"])})
    return clean(updated)
