import re
from fastapi import APIRouter, Depends

from core.db import db
from core.security import get_current_user
from core.utils import clean

router = APIRouter(prefix="/api")


@router.get("/search")
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
