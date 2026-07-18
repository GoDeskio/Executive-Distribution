from fastapi import APIRouter, Depends

from core.db import db
from core.security import require_superadmin
from core.utils import clean

router = APIRouter(prefix="/api")


@router.get("/audit")
async def list_audit(limit: int = 100, entity: str = None, action: str = None,
                     user: dict = Depends(require_superadmin)):
    q = {}
    if entity:
        q["entity"] = entity
    if action:
        q["action"] = action
    docs = await db.audit_logs.find(q).sort("created_at", -1).to_list(min(max(limit, 1), 500))
    return [clean(d) for d in docs]
