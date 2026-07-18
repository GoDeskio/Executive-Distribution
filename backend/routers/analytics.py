import re
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional

from core.db import db
from core.security import require_perm
from core.utils import clean, now_iso

router = APIRouter(prefix="/api")


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


@router.post("/track")
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


@router.get("/analytics/overview")
async def analytics_overview(user: dict = Depends(require_perm("dashboard"))):
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


@router.get("/analytics/timeseries")
async def analytics_timeseries(days: int = 14, user: dict = Depends(require_perm("dashboard"))):
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


@router.get("/analytics/pages")
async def analytics_pages(user: dict = Depends(require_perm("dashboard"))):
    pipeline = [
        {"$match": {"event_type": "pageview"}},
        {"$group": {"_id": "$path", "views": {"$sum": 1}}},
        {"$sort": {"views": -1}},
        {"$limit": 20},
    ]
    rows = await db.events.aggregate(pipeline).to_list(20)
    return [{"path": r["_id"], "views": r["views"]} for r in rows]


@router.get("/analytics/heatmap")
async def analytics_heatmap(path: str = "/", user: dict = Depends(require_perm("dashboard"))):
    docs = await db.events.find(
        {"event_type": "click", "path": path, "x": {"$ne": None}, "y": {"$ne": None}},
        {"x": 1, "y": 1, "_id": 0}
    ).sort("created_at", -1).to_list(3000)
    return [{"x": d["x"], "y": d["y"]} for d in docs]


@router.get("/analytics/visitors")
async def analytics_visitors(user: dict = Depends(require_perm("dashboard"))):
    docs = await db.visitors.find({}).sort("last_seen", -1).to_list(500)
    return [clean(d) for d in docs]
