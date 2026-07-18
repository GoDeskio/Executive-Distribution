from core.db import db
from core.utils import now_iso, logger


async def log_action(user, action, entity, entity_id=None, detail=""):
    """Best-effort audit trail. Never raises to the caller."""
    try:
        u = user or {}
        await db.audit_logs.insert_one({
            "user_id": u.get("id"),
            "user_email": u.get("email"),
            "user_name": u.get("name"),
            "action": action,          # login | create | update | delete | generate | share | password
            "entity": entity,          # auth | user | client | quote | document | service | file | settings
            "entity_id": entity_id,
            "detail": detail,
            "created_at": now_iso(),
        })
    except Exception as e:
        logger.warning(f"audit log failed: {e}")
