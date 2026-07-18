import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, Depends
from bson import ObjectId

from core.db import db
from core.config import JWT_SECRET, JWT_ALGORITHM
from core.utils import clean


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get("active") is False:
            raise HTTPException(status_code=403, detail="Account disabled")
        return clean(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def is_super(user: dict) -> bool:
    return user.get("role") == "superadmin"


async def require_superadmin(user: dict = Depends(get_current_user)) -> dict:
    if not is_super(user):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return user


def require_perm(perm: str):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if is_super(user) or perm in (user.get("permissions") or []):
            return user
        raise HTTPException(status_code=403, detail=f"You don't have access to the {perm} section")
    return checker


def require_any_perm(*perms):
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        ups = user.get("permissions") or []
        if is_super(user) or any(p in ups for p in perms):
            return user
        raise HTTPException(status_code=403, detail="You don't have access to this section")
    return checker
