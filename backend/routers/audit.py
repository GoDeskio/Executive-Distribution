import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

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


@router.get("/audit/export.csv")
async def export_audit(entity: str = None, action: str = None, user: dict = Depends(require_superadmin)):
    q = {}
    if entity:
        q["entity"] = entity
    if action:
        q["action"] = action
    docs = await db.audit_logs.find(q).sort("created_at", -1).to_list(5000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["created_at", "user_email", "user_name", "action", "entity", "entity_id", "detail"])
    for d in docs:
        writer.writerow([d.get("created_at", ""), d.get("user_email", ""), d.get("user_name", ""),
                         d.get("action", ""), d.get("entity", ""), d.get("entity_id", ""), d.get("detail", "")])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=audit-log.csv"})
