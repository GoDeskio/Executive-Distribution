from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Form, Query, Header
from fastapi.responses import Response, StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, BeforeValidator, EmailStr
from typing import List, Optional, Annotated, Any
from bson import ObjectId
from datetime import datetime, timezone, timedelta
import logging
import uuid
import re
import jwt
import bcrypt
import requests

# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = "HS256"
APP_NAME = "executive-distribution"
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mongo helpers
# ---------------------------------------------------------------------------
PyObjectId = Annotated[str, BeforeValidator(str)]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def slugify(text: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9\s-]', '', text or '').strip().lower()
    s = re.sub(r'[\s_-]+', '-', s)
    return s or str(uuid.uuid4())[:8]


def clean(doc):
    if not doc:
        return doc
    doc = dict(doc)
    doc['id'] = str(doc.pop('_id')) if '_id' in doc else doc.get('id')
    doc.pop('password_hash', None)
    return doc


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
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
        return clean(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Object storage (portable — see storage.py)
# ---------------------------------------------------------------------------
from storage import init_storage, put_object, get_object
import ai as ai_helper
from pdf_utils import generate_document_pdf


MIME_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif",
              "webp": "image/webp", "svg": "image/svg+xml", "pdf": "application/pdf",
              "json": "application/json", "csv": "text/csv", "txt": "text/plain",
              "doc": "application/msword", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class LoginInput(BaseModel):
    email: EmailStr
    password: str


class ServiceInput(BaseModel):
    title: str
    short_description: str = ""
    full_description: str = ""
    image_url: str = ""
    icon: str = "package"
    order: int = 0
    published: bool = True
    features: List[str] = []
    sections: List[dict] = []
    meta_title: str = ""
    meta_description: str = ""
    keywords: str = ""


class ClientInput(BaseModel):
    name: str
    company: str = ""
    email: str = ""
    phone: str = ""
    status: str = "lead"
    value: float = 0
    tags: List[str] = []
    notes: str = ""


class TrackInput(BaseModel):
    session_id: str
    path: str
    event_type: str = "pageview"  # pageview | click | scroll
    x: Optional[float] = None
    y: Optional[float] = None
    referrer: str = ""
    viewport_w: Optional[int] = None
    viewport_h: Optional[int] = None
    scroll_depth: Optional[float] = None


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@api_router.post("/auth/login")
async def login(data: LoginInput):
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(str(user["_id"]), email)
    return {"token": token, "user": clean(user)}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@api_router.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"ok": True}


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


@api_router.put("/auth/profile")
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


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
@api_router.get("/services")
async def list_services(all: bool = False, user_check: bool = False):
    q = {} if all else {"published": True}
    docs = await db.services.find(q).sort("order", 1).to_list(500)
    return [clean(d) for d in docs]


@api_router.get("/services/{slug}")
async def get_service(slug: str):
    doc = await db.services.find_one({"slug": slug})
    if not doc:
        doc = await db.services.find_one({"_id": ObjectId(slug)}) if ObjectId.is_valid(slug) else None
    if not doc:
        raise HTTPException(status_code=404, detail="Service not found")
    return clean(doc)


@api_router.post("/services")
async def create_service(data: ServiceInput, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    base = slugify(data.title)
    slug = base
    i = 1
    while await db.services.find_one({"slug": slug}):
        slug = f"{base}-{i}"
        i += 1
    doc["slug"] = slug
    doc["created_at"] = now_iso()
    doc["updated_at"] = now_iso()
    res = await db.services.insert_one(doc)
    return clean(await db.services.find_one({"_id": res.inserted_id}))


@api_router.put("/services/{service_id}")
async def update_service(service_id: str, data: ServiceInput, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["updated_at"] = now_iso()
    await db.services.update_one({"_id": ObjectId(service_id)}, {"$set": doc})
    return clean(await db.services.find_one({"_id": ObjectId(service_id)}))


@api_router.delete("/services/{service_id}")
async def delete_service(service_id: str, user: dict = Depends(get_current_user)):
    await db.services.delete_one({"_id": ObjectId(service_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Site settings (singleton) + SEO
# ---------------------------------------------------------------------------
@api_router.get("/settings")
async def get_settings():
    doc = await db.settings.find_one({"_id": "site"})
    if not doc:
        return {}
    doc.pop("_id", None)
    own = (doc.pop("ai_own_key", "") or "").strip()
    doc["has_own_key"] = bool(own)
    return doc


@api_router.put("/settings")
async def update_settings(payload: dict, user: dict = Depends(get_current_user)):
    payload.pop("_id", None)
    await db.settings.update_one({"_id": "site"}, {"$set": payload}, upsert=True)
    doc = await db.settings.find_one({"_id": "site"})
    doc.pop("_id", None)
    return doc


# ---------------------------------------------------------------------------
# CRM: Clients
# ---------------------------------------------------------------------------
@api_router.get("/clients")
async def list_clients(user: dict = Depends(get_current_user)):
    docs = await db.clients.find({}).sort("created_at", -1).to_list(1000)
    return [clean(d) for d in docs]


@api_router.post("/clients")
async def create_client(data: ClientInput, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["created_at"] = now_iso()
    res = await db.clients.insert_one(doc)
    return clean(await db.clients.find_one({"_id": res.inserted_id}))


@api_router.put("/clients/{client_id}")
async def update_client(client_id: str, data: ClientInput, user: dict = Depends(get_current_user)):
    await db.clients.update_one({"_id": ObjectId(client_id)}, {"$set": data.model_dump()})
    return clean(await db.clients.find_one({"_id": ObjectId(client_id)}))


@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, user: dict = Depends(get_current_user)):
    await db.clients.delete_one({"_id": ObjectId(client_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Quote Requests (public intake -> CRM)
# ---------------------------------------------------------------------------
def _store_upload(data: bytes, filename: str, content_type: str, category: str):
    ext = filename.split(".")[-1].lower() if "." in filename else "bin"
    path = f"{APP_NAME}/{category}/{uuid.uuid4()}.{ext}"
    ctype = content_type or MIME_TYPES.get(ext, "application/octet-stream")
    result = put_object(path, data, ctype)
    return result["path"], ctype, result.get("size", len(data))


@api_router.post("/quotes")
async def create_quote(
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(""),
    phone: str = Form(""),
    destination: str = Form(""),
    description: str = Form(""),
    images: List[UploadFile] = File(default=[]),
):
    image_urls = []
    for img in images or []:
        if not img or not img.filename:
            continue
        data = await img.read()
        if not data:
            continue
        storage_path, ctype, size = _store_upload(data, img.filename, img.content_type, "quote")
        rec = {
            "storage_path": storage_path, "original_filename": img.filename,
            "content_type": ctype, "size": size, "category": "quote",
            "client_id": None, "is_deleted": False, "created_at": now_iso(),
        }
        res = await db.files.insert_one(rec)
        image_urls.append(f"/api/files/{str(res.inserted_id)}/raw")

    doc = {
        "name": name, "email": email, "company": company, "phone": phone,
        "destination": destination, "description": description,
        "images": image_urls, "status": "new", "notes": "", "created_at": now_iso(),
    }
    r = await db.quotes.insert_one(doc)
    return {"ok": True, "id": str(r.inserted_id)}


class QuoteUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


@api_router.get("/quotes")
async def list_quotes(user: dict = Depends(get_current_user)):
    docs = await db.quotes.find({}).sort("created_at", -1).to_list(1000)
    return [clean(d) for d in docs]


@api_router.put("/quotes/{quote_id}")
async def update_quote(quote_id: str, data: QuoteUpdate, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.quotes.update_one({"_id": ObjectId(quote_id)}, {"$set": updates})
    return clean(await db.quotes.find_one({"_id": ObjectId(quote_id)}))


@api_router.delete("/quotes/{quote_id}")
async def delete_quote(quote_id: str, user: dict = Depends(get_current_user)):
    await db.quotes.delete_one({"_id": ObjectId(quote_id)})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Files: assets & documents
# ---------------------------------------------------------------------------
@api_router.post("/files/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form("asset"),
                      client_id: str = Form(""), user: dict = Depends(get_current_user)):
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


@api_router.get("/files")
async def list_files(category: str = None, user: dict = Depends(get_current_user)):
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


@api_router.get("/files/{file_id}/raw")
async def serve_file(file_id: str):
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=404, detail="Not found")
    record = await db.files.find_one({"_id": ObjectId(file_id), "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    data, ctype = get_object(record["storage_path"])
    return Response(content=data, media_type=record.get("content_type", ctype))


@api_router.delete("/files/{file_id}")
async def delete_file(file_id: str, user: dict = Depends(get_current_user)):
    await db.files.update_one({"_id": ObjectId(file_id)}, {"$set": {"is_deleted": True}})
    return {"ok": True}


# ---------------------------------------------------------------------------
# Visitor tracking & analytics
# ---------------------------------------------------------------------------
@api_router.post("/track")
async def track(data: TrackInput, request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    ua = request.headers.get("user-agent", "")
    device = "mobile" if re.search(r"Mobi|Android|iPhone", ua) else "desktop"
    ts = now_iso()

    event = {
        "session_id": data.session_id,
        "path": data.path,
        "event_type": data.event_type,
        "x": data.x, "y": data.y,
        "viewport_w": data.viewport_w, "viewport_h": data.viewport_h,
        "scroll_depth": data.scroll_depth,
        "ip": ip, "device": device, "created_at": ts,
    }
    await db.events.insert_one(event)

    if data.event_type == "pageview":
        await db.visitors.update_one(
            {"session_id": data.session_id},
            {"$set": {"last_seen": ts, "ip": ip, "device": device, "user_agent": ua,
                      "last_path": data.path},
             "$inc": {"page_views": 1},
             "$setOnInsert": {"session_id": data.session_id, "first_seen": ts,
                              "referrer": data.referrer}},
            upsert=True,
        )
    return {"ok": True}


@api_router.get("/analytics/overview")
async def analytics_overview(user: dict = Depends(get_current_user)):
    total_visitors = await db.visitors.count_documents({})
    total_views = await db.events.count_documents({"event_type": "pageview"})
    total_clients = await db.clients.count_documents({})
    total_services = await db.services.count_documents({})
    total_quotes = await db.quotes.count_documents({})
    new_quotes = await db.quotes.count_documents({"status": "new"})
    since = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    active = len(await db.visitors.distinct("session_id", {"last_seen": {"$gte": since}}))
    devices = await db.visitors.aggregate([{"$group": {"_id": "$device", "count": {"$sum": 1}}}]).to_list(10)
    return {
        "total_visitors": total_visitors,
        "total_views": total_views,
        "total_clients": total_clients,
        "total_services": total_services,
        "total_quotes": total_quotes,
        "new_quotes": new_quotes,
        "active_now": active,
        "devices": {d["_id"] or "unknown": d["count"] for d in devices},
    }


@api_router.get("/analytics/timeseries")
async def analytics_timeseries(days: int = 14, user: dict = Depends(get_current_user)):
    start = datetime.now(timezone.utc) - timedelta(days=days)
    pipeline = [
        {"$match": {"event_type": "pageview", "created_at": {"$gte": start.isoformat()}}},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "views": {"$sum": 1},
                    "visitors": {"$addToSet": "$session_id"}}},
        {"$sort": {"_id": 1}},
    ]
    rows = await db.events.aggregate(pipeline).to_list(100)
    result = []
    for i in range(days, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        match = next((r for r in rows if r["_id"] == day), None)
        result.append({"date": day, "views": match["views"] if match else 0,
                       "visitors": len(match["visitors"]) if match else 0})
    return result


@api_router.get("/analytics/pages")
async def analytics_pages(user: dict = Depends(get_current_user)):
    pipeline = [
        {"$match": {"event_type": "pageview"}},
        {"$group": {"_id": "$path", "views": {"$sum": 1}}},
        {"$sort": {"views": -1}},
        {"$limit": 20},
    ]
    rows = await db.events.aggregate(pipeline).to_list(20)
    return [{"path": r["_id"], "views": r["views"]} for r in rows]


@api_router.get("/analytics/heatmap")
async def analytics_heatmap(path: str = "/", user: dict = Depends(get_current_user)):
    docs = await db.events.find(
        {"event_type": "click", "path": path, "x": {"$ne": None}, "y": {"$ne": None}},
        {"x": 1, "y": 1, "_id": 0}
    ).sort("created_at", -1).to_list(3000)
    return [{"x": d["x"], "y": d["y"]} for d in docs]


@api_router.get("/analytics/visitors")
async def analytics_visitors(user: dict = Depends(get_current_user)):
    docs = await db.visitors.find({}).sort("last_seen", -1).to_list(500)
    return [clean(d) for d in docs]


# ---------------------------------------------------------------------------
# AI Assistant (chat)
# ---------------------------------------------------------------------------
async def _get_settings_doc():
    doc = await db.settings.find_one({"_id": "site"}) or {}
    doc.pop("_id", None)
    return doc


PUBLIC_SYSTEM = (
    "You are the Executive Distribution AI concierge on a premium import/export & product sourcing "
    "company website. You help visitors estimate shipping fees, explain which documents they will need "
    "for customs/shipping, and answer questions about services (freight forwarding, port logistics, "
    "cigar sourcing, coffee distribution, Larimar/mineral supply, warehousing). Be concise, professional "
    "and helpful. When a visitor wants a formal quote, encourage them to submit the Request a Quote form "
    "with item details, destination and reference images. Never invent client data. Give fee figures as "
    "clearly-labeled estimates."
)

ADMIN_SYSTEM = (
    "You are the Executive Distribution operations assistant for staff. You act as a logistics calculator "
    "and documentation expert: compute and explain shipping fees, customs duties and taxes, and list the "
    "exact documents required for a given shipment (e.g. commercial invoice, packing list, bill of lading, "
    "certificate of origin, import/export licenses, insurance certificate, phytosanitary/CITES where relevant). "
    "Help draft quotes and receipts and organize records per client. Be precise, use clear line-item "
    "breakdowns, and state assumptions."
)


class ChatInput(BaseModel):
    session_id: str
    message: str
    history: List[dict] = []
    scope: str = "public"  # public | admin


async def _chat_stream(payload: ChatInput, is_admin: bool):
    settings = await _get_settings_doc()
    system = ADMIN_SYSTEM if is_admin else PUBLIC_SYSTEM
    collected = []

    async def gen():
        async for chunk in ai_helper.stream_reply(payload.session_id, system, payload.history, payload.message, settings):
            collected.append(chunk)
            yield chunk
        # persist
        try:
            await db.chat_messages.insert_one({
                "session_id": payload.session_id, "scope": "admin" if is_admin else "public",
                "user": payload.message, "assistant": "".join(collected), "created_at": now_iso(),
            })
        except Exception:
            pass

    return StreamingResponse(gen(), media_type="text/plain",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@api_router.post("/ai/chat")
async def ai_chat_public(payload: ChatInput):
    return await _chat_stream(payload, is_admin=False)


@api_router.post("/ai/chat/admin")
async def ai_chat_admin(payload: ChatInput, user: dict = Depends(get_current_user)):
    return await _chat_stream(payload, is_admin=True)


@api_router.get("/ai/status")
async def ai_status(user: dict = Depends(get_current_user)):
    settings = await _get_settings_doc()
    cfg = ai_helper.resolve_ai_config(settings)
    return {"source": cfg["source"], "provider": cfg["provider"], "model": cfg["model"],
            "has_own_key": bool((settings.get("ai_own_key") or "").strip())}


# ---------------------------------------------------------------------------
# Fee / customs calculator (rule-based) + AI document guidance
# ---------------------------------------------------------------------------
DEFAULT_FEE_RULES = {
    "freight_rate_per_kg": 4.5,
    "handling_fee_flat": 75.0,
    "insurance_pct": 1.5,
    "duty_pct": 8.0,
    "vat_pct": 5.0,
    "port_surcharge": 120.0,
}


class CalcInput(BaseModel):
    item_name: str = ""
    declared_value: float = 0
    weight_kg: float = 0
    quantity: int = 1
    origin: str = ""
    destination: str = ""
    mode: str = "ocean"  # ocean | air | ground


@api_router.post("/calculate")
async def calculate(data: CalcInput):
    settings = await _get_settings_doc()
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


# ---------------------------------------------------------------------------
# Documents / Quotes builder (formal quotes, receipts, customs docs)
# ---------------------------------------------------------------------------
class LineItem(BaseModel):
    item: str = ""
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


async def _next_number(doc_type: str) -> str:
    prefix = {"quote": "EXD-Q", "receipt": "EXD-R", "customs": "EXD-C"}.get(doc_type, "EXD")
    count = await db.documents.count_documents({"doc_type": doc_type}) + 1
    return f"{prefix}-{count:05d}"


@api_router.get("/documents")
async def list_documents(user: dict = Depends(get_current_user)):
    docs = await db.documents.find({}).sort("created_at", -1).to_list(1000)
    return [clean(d) for d in docs]


@api_router.post("/documents")
async def create_document(data: DocumentInput, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["line_items"] = [li for li in doc["line_items"]]
    doc["number"] = await _next_number(data.doc_type)
    if not doc.get("date"):
        doc["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc["created_at"] = now_iso()
    doc["pdf_file_id"] = None
    res = await db.documents.insert_one(doc)
    return clean(await db.documents.find_one({"_id": res.inserted_id}))


@api_router.put("/documents/{doc_id}")
async def update_document(doc_id: str, data: DocumentInput, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    await db.documents.update_one({"_id": ObjectId(doc_id)}, {"$set": doc})
    return clean(await db.documents.find_one({"_id": ObjectId(doc_id)}))


@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    await db.documents.delete_one({"_id": ObjectId(doc_id)})
    return {"ok": True}


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


@api_router.post("/documents/{doc_id}/generate")
async def generate_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    settings = await _get_settings_doc()
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


# ---------------------------------------------------------------------------
# Global search
# ---------------------------------------------------------------------------
@api_router.get("/search")
async def global_search(q: str = "", user: dict = Depends(get_current_user)):
    q = (q or "").strip()
    if not q:
        return {"clients": [], "quotes": [], "requests": [], "documents": []}
    rx = {"$regex": re.escape(q), "$options": "i"}

    clients = await db.clients.find({"$or": [
        {"name": rx}, {"email": rx}, {"phone": rx}, {"company": rx},
    ]}).limit(25).to_list(25)

    requests_ = await db.quotes.find({"$or": [
        {"name": rx}, {"email": rx}, {"phone": rx}, {"company": rx},
        {"destination": rx}, {"description": rx},
    ]}).limit(25).to_list(25)

    documents = await db.documents.find({"$or": [
        {"client_name": rx}, {"client_email": rx}, {"client_phone": rx}, {"client_company": rx},
        {"number": rx}, {"po_number": rx}, {"tracking_number": rx}, {"port": rx},
        {"destination": rx}, {"date": rx}, {"line_items.item": rx},
    ]}).limit(25).to_list(25)

    return {
        "clients": [clean(c) for c in clients],
        "requests": [clean(r) for r in requests_],
        "documents": [clean(d) for d in documents],
    }


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
DEFAULT_SERVICES = [
    {"title": "Global Import & Export", "icon": "ship",
     "image_url": "https://images.unsplash.com/photo-1568347877321-f8935c7dc5a3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA0MTJ8MHwxfHNlYXJjaHwxfHxjYXJnbyUyMHNoaXAlMjBmcmVpZ2h0ZXIlMjBuaWdodHxlbnwwfHx8fDE3ODQzOTA0Njd8MA&ixlib=rb-4.1.0&q=85",
     "short_description": "End-to-end freight forwarding across every major trade lane, handled with executive precision.",
     "full_description": "Executive Distribution moves cargo across oceans with the discipline of a private logistics firm. From documentation and customs clearance to last-mile delivery, we orchestrate the full lifecycle of your international shipments. Our network of carriers, brokers, and bonded warehouses ensures your goods arrive intact, compliant, and on schedule.",
     "features": ["Ocean & air freight forwarding", "Customs brokerage & compliance", "Bonded warehousing", "Real-time shipment tracking"]},
    {"title": "Port & Logistics Management", "icon": "anchor",
     "image_url": "https://images.unsplash.com/photo-1554769944-3138b076c38a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzV8MHwxfHNlYXJjaHwxfHxpbmR1c3RyaWFsJTIwcG9ydCUyMGRyb25lfGVufDB8fHx8MTc4NDM5MDQ2N3ww&ixlib=rb-4.1.0&q=85",
     "short_description": "Container handling, drayage and terminal coordination at the world's busiest ports.",
     "full_description": "Our port operations team manages terminal relationships, container drayage, and yard coordination so your freight never sits idle. We negotiate priority berthing, optimize container turnaround, and provide transparent reporting at every touchpoint.",
     "features": ["Terminal & berth coordination", "Container drayage", "Yard & inventory management", "Demurrage mitigation"]},
    {"title": "Premium Cigar Sourcing", "icon": "flame",
     "image_url": "https://images.pexels.com/photos/3975055/pexels-photo-3975055.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
     "short_description": "Direct-from-factory sourcing of hand-rolled cigars from the Caribbean's finest houses.",
     "full_description": "We maintain direct relationships with heritage cigar factories, giving our clients access to limited allocations of hand-rolled, aged tobacco. Every shipment is climate-controlled, authenticated, and fully documented for import.",
     "features": ["Factory-direct allocations", "Climate-controlled transport", "Authentication & grading", "Full import documentation"]},
    {"title": "Coffee Bean Distribution", "icon": "coffee",
     "image_url": "https://images.unsplash.com/photo-1606486544554-164d98da4889?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1MDV8MHwxfHNlYXJjaHwzfHxjb2ZmZWUlMjBiZWFuJTIwZGlzdHJpYnV0aW9ufGVufDB8fHx8MTc4NDM5MDQ2N3ww&ixlib=rb-4.1.0&q=85",
     "short_description": "Single-origin green coffee, sourced ethically and delivered at scale to roasters worldwide.",
     "full_description": "From highland estates to your roastery, we manage the sourcing, grading, and logistics of premium green coffee. Our traceable supply chain guarantees quality and ethical origin at commercial volumes.",
     "features": ["Single-origin sourcing", "Cupping & grading", "Traceable supply chain", "Volume contracts"]},
    {"title": "Larimar & Mineral Supply", "icon": "gem",
     "image_url": "https://images.unsplash.com/photo-1767131545090-e13ae86c8e13?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzJ8MHwxfHNlYXJjaHwzfHxibHVlJTIwZ2Vtc3RvbmUlMjByb3VnaHxlbnwwfHx8fDE3ODQzOTA0NzR8MA&ixlib=rb-4.1.0&q=85",
     "short_description": "Exclusive access to rare Larimar and semi-precious minerals from protected sources.",
     "full_description": "As one of few distributors with licensed access to Larimar mines, we supply raw and polished stone to jewelers and collectors. Each lot is certified for authenticity and origin.",
     "features": ["Licensed mine access", "Raw & polished lots", "Authenticity certification", "Export licensing"]},
    {"title": "Warehousing & Fulfillment", "icon": "warehouse",
     "image_url": "https://images.pexels.com/photos/4487365/pexels-photo-4487365.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
     "short_description": "Secure distribution centers with real-time inventory and white-glove fulfillment.",
     "full_description": "Our distribution centers combine secure storage with intelligent inventory systems and hands-on fulfillment teams. Whether you need bulk staging or pick-and-pack, our managers treat your goods as their own.",
     "features": ["Secure climate storage", "Real-time inventory", "Pick, pack & ship", "Dedicated account managers"]},
]

DEFAULT_SETTINGS = {
    "company_name": "Executive Distribution",
    "logo_url": "",
    "tagline": "Global Sourcing. Executive Delivery.",
    "hero_title": "Moving the World's Finest Goods With Executive Precision",
    "hero_subtitle": "Executive Distribution is a private import/export and product sourcing firm connecting discerning clients to premium goods across the globe — freight, logistics, and rare commodities under one roof.",
    "hero_image": "https://images.pexels.com/photos/14734004/pexels-photo-14734004.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "hero_cta": "Explore Our Services",
    "about_text": "For over two decades, Executive Distribution has quietly powered the supply chains of luxury brands, boutique roasters, jewelers, and importers. We operate where precision meets discretion.",
    "about_image": "https://images.pexels.com/photos/4487365/pexels-photo-4487365.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
    "contact_email": "contact@executivedistribution.com",
    "phone": "+1 (305) 555-0142",
    "address": "1200 Brickell Bay Drive, Miami, FL",
    "linkedin": "#", "twitter": "#", "instagram": "#",
    "footer_text": "Executive Distribution — Global import/export & product sourcing.",
    "seo_title": "Executive Distribution | Global Import, Export & Product Sourcing",
    "seo_description": "Premium import/export and product sourcing. Freight forwarding, port logistics, cigars, coffee, Larimar and warehousing — handled with executive precision.",
    "seo_keywords": "import export, product sourcing, freight forwarding, cigar sourcing, coffee distribution, larimar supply, warehousing",
    "ai_provider": "openai",
    "ai_model": "gpt-5.4",
    "ai_use_own_key": False,
    "ai_own_key": "",
    "fee_rules": {
        "freight_rate_per_kg": 4.5,
        "handling_fee_flat": 75.0,
        "insurance_pct": 1.5,
        "duty_pct": 8.0,
        "vat_pct": 5.0,
        "port_surcharge": 120.0,
    },
}


@app.on_event("startup")
async def startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.services.create_index("slug", unique=True)
        await db.visitors.create_index("session_id", unique=True)
        await db.events.create_index([("path", 1), ("event_type", 1)])
    except Exception as e:
        logger.warning(f"Index warning: {e}")

    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_password = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_password),
                                   "name": "Executive Admin", "role": "admin", "avatar_url": "",
                                   "created_at": now_iso()})
        logger.info("Seeded admin user")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email},
                                  {"$set": {"password_hash": hash_password(admin_password)}})

    if await db.services.count_documents({}) == 0:
        for i, s in enumerate(DEFAULT_SERVICES):
            s = dict(s)
            s.update({"slug": slugify(s["title"]), "order": i, "published": True,
                      "sections": [], "meta_title": s["title"], "meta_description": s["short_description"],
                      "keywords": "", "created_at": now_iso(), "updated_at": now_iso()})
            await db.services.insert_one(s)
        logger.info("Seeded default services")

    if not await db.settings.find_one({"_id": "site"}):
        doc = dict(DEFAULT_SETTINGS)
        doc["_id"] = "site"
        await db.settings.insert_one(doc)
        logger.info("Seeded site settings")

    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
