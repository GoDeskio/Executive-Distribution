from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List

from core.db import db
from core.security import require_perm, get_current_user
from core.utils import now_iso
from core.settings_store import get_settings_doc, PUBLIC_SYSTEM, ADMIN_SYSTEM, DEFAULT_FEE_RULES
import ai as ai_helper

router = APIRouter(prefix="/api")


class ChatInput(BaseModel):
    session_id: str
    message: str
    history: List[dict] = []
    scope: str = "public"  # public | admin


class CalcInput(BaseModel):
    item_name: str = ""
    declared_value: float = 0
    weight_kg: float = 0
    quantity: int = 1
    origin: str = ""
    destination: str = ""
    mode: str = "ocean"  # ocean | air | ground


async def _chat_stream(payload: ChatInput, is_admin: bool):
    settings = await get_settings_doc()
    system = ADMIN_SYSTEM if is_admin else PUBLIC_SYSTEM
    collected = []

    async def gen():
        async for chunk in ai_helper.stream_reply(payload.session_id, system, payload.history, payload.message, settings):
            collected.append(chunk)
            yield chunk
        try:
            await db.chat_messages.insert_one({
                "session_id": payload.session_id, "scope": "admin" if is_admin else "public",
                "user": payload.message, "assistant": "".join(collected), "created_at": now_iso(),
            })
        except Exception:
            pass

    return StreamingResponse(gen(), media_type="text/plain",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/ai/chat")
async def ai_chat_public(payload: ChatInput):
    return await _chat_stream(payload, is_admin=False)


@router.post("/ai/chat/admin")
async def ai_chat_admin(payload: ChatInput, user: dict = Depends(require_perm("ai"))):
    return await _chat_stream(payload, is_admin=True)


@router.get("/ai/status")
async def ai_status(user: dict = Depends(get_current_user)):
    settings = await get_settings_doc()
    cfg = ai_helper.resolve_ai_config(settings)
    return {"source": cfg["source"], "provider": cfg["provider"], "model": cfg["model"],
            "has_own_key": bool((settings.get("ai_own_key") or "").strip())}


@router.post("/calculate")
async def calculate(data: CalcInput):
    settings = await get_settings_doc()
    rules = {**DEFAULT_FEE_RULES, **(settings.get("fee_rules") or {})}
    mode_mult = {"ocean": 1.0, "air": 2.6, "ground": 0.7}.get(data.mode, 1.0)

    freight = data.weight_kg * rules["freight_rate_per_kg"] * mode_mult * max(data.quantity, 1)
    handling = rules["handling_fee_flat"]
    port = rules["port_surcharge"]
    insurance = data.declared_value * rules["insurance_pct"] / 100.0
    customs = data.declared_value * rules["duty_pct"] / 100.0
    taxable = data.declared_value + freight + customs
    vat = taxable * rules["vat_pct"] / 100.0
    fees_total = round(freight + handling + port + insurance, 2)
    grand = round(data.declared_value + fees_total + customs + vat, 2)

    return {
        "breakdown": {
            "declared_value": round(data.declared_value, 2),
            "freight": round(freight, 2),
            "handling": round(handling, 2),
            "port_surcharge": round(port, 2),
            "insurance": round(insurance, 2),
            "customs_duty": round(customs, 2),
            "vat_tax": round(vat, 2),
        },
        "fees_total": fees_total,
        "customs_total": round(customs, 2),
        "tax_total": round(vat, 2),
        "grand_total": grand,
        "rules_used": rules,
    }
