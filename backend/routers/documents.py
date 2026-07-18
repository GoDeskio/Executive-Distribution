import json
import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import requests
from bson import ObjectId

from core.db import db
from core.config import APP_NAME
from core.security import require_perm
from core.utils import clean, now_iso, logger
from core.settings_store import get_settings_doc, DEFAULT_FEE_RULES
import ai as ai_helper
from storage import put_object, get_object
from pdf_utils import generate_document_pdf

router = APIRouter(prefix="/api")


class LineItem(BaseModel):
    item: str = ""
    hs_code: str = ""
    qty: float = 1
    unit_price: float = 0
    fees: float = 0
    customs: float = 0
    total: float = 0


class DocumentInput(BaseModel):
    doc_type: str = "quote"  # quote | receipt | customs
    client_id: str = ""
    client_name: str = ""
    client_company: str = ""
    client_email: str = ""
    client_phone: str = ""
    destination: str = ""
    port: str = ""
    po_number: str = ""
    tracking_number: str = ""
    date: str = ""
    line_items: List[LineItem] = []
    subtotal: float = 0
    fees_total: float = 0
    customs_total: float = 0
    tax_total: float = 0
    grand_total: float = 0
    notes: str = ""
    status: str = "draft"
    shared: bool = True


class AiDraftInput(BaseModel):
    description: str
    client_id: str = ""
    client_name: str = ""
    doc_type: str = "quote"


async def _next_number(doc_type: str) -> str:
    prefix = {"quote": "EXD-Q", "receipt": "EXD-R", "customs": "EXD-C"}.get(doc_type, "EXD")
    count = await db.documents.count_documents({"doc_type": doc_type}) + 1
    return f"{prefix}-{count:05d}"


def _compute_line(declared_value, weight_kg, qty, mode, rules):
    mode_mult = {"ocean": 1.0, "air": 2.6, "ground": 0.7}.get(mode, 1.0)
    freight = float(weight_kg) * rules["freight_rate_per_kg"] * mode_mult
    insurance = float(declared_value) * rules["insurance_pct"] / 100.0
    customs = float(declared_value) * rules["duty_pct"] / 100.0
    return round(freight + insurance, 2), round(customs, 2)


async def _fetch_logo_bytes(settings: dict):
    logo_url = settings.get("logo_url") or ""
    try:
        if logo_url.startswith("/api/files/"):
            fid = logo_url.split("/api/files/")[1].split("/")[0]
            rec = await db.files.find_one({"_id": ObjectId(fid)})
            if rec:
                data, _ = get_object(rec["storage_path"])
                return data
        elif logo_url.startswith("http"):
            r = requests.get(logo_url, timeout=15)
            if r.ok:
                return r.content
    except Exception as e:
        logger.warning(f"logo fetch failed: {e}")
    return None


@router.post("/documents/ai-draft")
async def ai_draft_document(data: AiDraftInput, user: dict = Depends(require_perm("documents"))):
    settings = await get_settings_doc()
    rules = {**DEFAULT_FEE_RULES, **(settings.get("fee_rules") or {})}

    system = ("You are a logistics quoting assistant for an import/export firm. "
              "Extract shipment line items from the user's description. Respond with STRICT JSON only, no prose, no markdown fences.")
    prompt = (
        'Return ONLY valid JSON with this exact shape:\n'
        '{"destination": "", "port": "", "notes": "", "line_items": '
        '[{"item": "", "hs_code": "", "qty": 1, "unit_price": 0, "weight_kg": 0, "declared_value": 0, "mode": "ocean"}]}\n'
        "- hs_code: the most likely 6-digit Harmonized System (HS) tariff code for the item (best estimate, digits only)\n"
        "- unit_price: estimated USD price per unit (0 if unknown)\n"
        "- declared_value: total customs value for the line in USD (qty*unit_price if unknown)\n"
        "- weight_kg: estimated total weight for the line in kg\n"
        '- mode: one of "ocean", "air", "ground"\n'
        "- notes: a short bullet list of the shipping/customs documents required for this shipment\n\n"
        f'Shipment description: """{data.description}"""'
    )
    try:
        raw = await ai_helper.complete(f"draft-{uuid.uuid4()}", system, prompt, settings)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI request failed: {str(e)[:150]}")

    text = raw.strip()
    if "```" in text:
        text = re.sub(r"```[a-zA-Z]*", "", text).replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise HTTPException(status_code=422, detail="AI did not return structured data. Try rephrasing the description.")
    try:
        parsed = json.loads(text[start:end + 1])
    except Exception:
        raise HTTPException(status_code=422, detail="Could not parse the AI draft. Please try again.")

    line_items = []
    subtotal = fees_sum = customs_sum = 0.0
    for li in parsed.get("line_items", [])[:20]:
        qty = float(li.get("qty", 1) or 1)
        unit_price = float(li.get("unit_price", 0) or 0)
        declared = float(li.get("declared_value", 0) or (qty * unit_price))
        weight = float(li.get("weight_kg", 0) or 0)
        mode = li.get("mode", "ocean")
        fees_line, customs_line = _compute_line(declared, weight, qty, mode, rules)
        total = round(qty * unit_price + fees_line + customs_line, 2)
        line_items.append({"item": li.get("item", ""), "hs_code": str(li.get("hs_code", "") or ""),
                           "qty": qty, "unit_price": round(unit_price, 2),
                           "fees": fees_line, "customs": customs_line, "total": total})
        subtotal += qty * unit_price
        fees_sum += fees_line
        customs_sum += customs_line

    fees_total = round(fees_sum + rules["handling_fee_flat"] + rules["port_surcharge"], 2)
    customs_total = round(customs_sum, 2)
    subtotal = round(subtotal, 2)
    tax_total = round((subtotal + fees_total + customs_total) * rules["vat_pct"] / 100.0, 2)
    grand_total = round(subtotal + fees_total + customs_total + tax_total, 2)

    return {
        "doc_type": data.doc_type,
        "client_id": data.client_id,
        "client_name": data.client_name,
        "destination": parsed.get("destination", ""),
        "port": parsed.get("port", ""),
        "line_items": line_items or [{"item": "", "qty": 1, "unit_price": 0, "fees": 0, "customs": 0, "total": 0}],
        "subtotal": subtotal, "fees_total": fees_total, "customs_total": customs_total,
        "tax_total": tax_total, "grand_total": grand_total,
        "notes": parsed.get("notes", ""),
    }


@router.get("/documents")
async def list_documents(user: dict = Depends(require_perm("documents"))):
    docs = await db.documents.find({}).sort("created_at", -1).to_list(1000)
    return [clean(d) for d in docs]


@router.post("/documents")
async def create_document(data: DocumentInput, user: dict = Depends(require_perm("documents"))):
    doc = data.model_dump()
    doc["line_items"] = [li for li in doc["line_items"]]
    doc["number"] = await _next_number(data.doc_type)
    if not doc.get("date"):
        doc["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc["created_at"] = now_iso()
    doc["pdf_file_id"] = None
    res = await db.documents.insert_one(doc)
    return clean(await db.documents.find_one({"_id": res.inserted_id}))


@router.put("/documents/{doc_id}")
async def update_document(doc_id: str, data: DocumentInput, user: dict = Depends(require_perm("documents"))):
    doc = data.model_dump()
    await db.documents.update_one({"_id": ObjectId(doc_id)}, {"$set": doc})
    return clean(await db.documents.find_one({"_id": ObjectId(doc_id)}))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(require_perm("documents"))):
    await db.documents.delete_one({"_id": ObjectId(doc_id)})
    return {"ok": True}


@router.post("/documents/{doc_id}/share")
async def toggle_share(doc_id: str, payload: dict, user: dict = Depends(require_perm("documents"))):
    shared = bool(payload.get("shared", True))
    await db.documents.update_one({"_id": ObjectId(doc_id)}, {"$set": {"shared": shared}})
    return {"ok": True, "shared": shared}


@router.post("/documents/{doc_id}/generate")
async def generate_document(doc_id: str, user: dict = Depends(require_perm("documents"))):
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    settings = await get_settings_doc()
    logo_bytes = await _fetch_logo_bytes(settings)
    pdf_bytes = generate_document_pdf(clean(dict(doc)), settings, logo_bytes)

    filename = f'{doc.get("number","document")}.pdf'
    path = f"{APP_NAME}/send-to-client/{uuid.uuid4()}.pdf"
    result = put_object(path, pdf_bytes, "application/pdf")
    frec = {
        "storage_path": result["path"], "original_filename": filename,
        "content_type": "application/pdf", "size": result.get("size", len(pdf_bytes)),
        "category": "send_to_client", "client_id": doc.get("client_id") or None,
        "document_id": str(doc["_id"]), "is_deleted": False, "created_at": now_iso(),
    }
    fres = await db.files.insert_one(frec)
    await db.documents.update_one({"_id": doc["_id"]},
                                  {"$set": {"pdf_file_id": str(fres.inserted_id), "status": "generated"}})
    return {"ok": True, "file_id": str(fres.inserted_id), "url": f"/api/files/{str(fres.inserted_id)}/raw"}
