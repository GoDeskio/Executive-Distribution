import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from bson import ObjectId

from core.db import db
from core.security import require_perm
from core.utils import clean, now_iso
from core.settings_store import get_settings_doc
from core.scraper import scrape_url
from core.audit import log_action

router = APIRouter(prefix="/api")

MAX_URLS = 15


class ScrapeInput(BaseModel):
    keywords: str = ""
    urls: List[str] = []
    render: bool = False
    respect_robots: bool = True


@router.post("/research/scrape")
async def research_scrape(data: ScrapeInput, user: dict = Depends(require_perm("research"))):
    urls = [u.strip() for u in data.urls if u and u.strip()][:MAX_URLS]
    if not urls:
        raise HTTPException(status_code=400, detail="Please enter at least one URL to scrape.")
    keywords = [k.strip() for k in data.keywords.replace("\n", ",").split(",") if k.strip()]

    settings = await get_settings_doc()
    api_key = (settings.get("scraperapi_key") or "").strip()

    results = []
    for url in urls:
        r = await asyncio.to_thread(scrape_url, url, keywords, data.render, api_key, data.respect_robots)
        results.append(r)

    doc = {
        "keywords": keywords,
        "keywords_raw": data.keywords,
        "urls": urls,
        "render": data.render,
        "results": results,
        "ok_count": sum(1 for r in results if r.get("status") == "ok"),
        "total_matches": sum(r.get("total_matches", 0) for r in results),
        "created_at": now_iso(),
        "user_email": user.get("email"),
    }
    res = await db.research.insert_one(doc)
    await log_action(user, "generate", "research", str(res.inserted_id),
                     f"{len(urls)} url(s), render={data.render}")
    return clean(await db.research.find_one({"_id": res.inserted_id}))


@router.get("/research")
async def list_research(user: dict = Depends(require_perm("research"))):
    docs = await db.research.find({}).sort("created_at", -1).to_list(100)
    return [clean(d) for d in docs]


@router.delete("/research/{research_id}")
async def delete_research(research_id: str, user: dict = Depends(require_perm("research"))):
    await db.research.delete_one({"_id": ObjectId(research_id)})
    await log_action(user, "delete", "research", research_id)
    return {"ok": True}
