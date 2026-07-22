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
import ai as ai_helper

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
    if not ObjectId.is_valid(research_id):
        raise HTTPException(status_code=404, detail="Not found")
    res = await db.research.delete_one({"_id": ObjectId(research_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    await log_action(user, "delete", "research", research_id)
    return {"ok": True}


AI_SUMMARY_SYSTEM = (
    "You are a sourcing & market-research analyst for Executive Distribution, an import/export and "
    "product-sourcing firm. You read scraped web pages and produce a concise, decision-ready brief. "
    "Be factual, only use what's in the provided content, and never invent data."
)


def _build_context(doc: dict) -> str:
    parts = []
    for r in doc.get("results", []):
        if r.get("status") != "ok":
            continue
        block = [f"URL: {r.get('url')}", f"Title: {r.get('title','')}"]
        if r.get("meta_description"):
            block.append(f"Meta: {r['meta_description']}")
        matches = [f"{m['keyword']} ({m['count']})" for m in r.get("keyword_matches", []) if m.get("count")]
        if matches:
            block.append("Keyword hits: " + ", ".join(matches))
        if r.get("emails"):
            block.append("Emails: " + ", ".join(r["emails"][:10]))
        if r.get("phones"):
            block.append("Phones: " + ", ".join(r["phones"][:10]))
        if r.get("text_excerpt"):
            block.append("Text: " + r["text_excerpt"][:2500])
        parts.append("\n".join(block))
    return "\n\n---\n\n".join(parts)[:14000]


@router.post("/research/{research_id}/summarize")
async def summarize_research(research_id: str, user: dict = Depends(require_perm("research"))):
    if not ObjectId.is_valid(research_id):
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.research.find_one({"_id": ObjectId(research_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Research run not found")
    context = _build_context(doc)
    if not context.strip():
        raise HTTPException(status_code=400, detail="No successfully scraped content to summarize.")

    keywords = ", ".join(doc.get("keywords", [])) or "(none)"
    prompt = (
        f"Research keywords: {keywords}\n\n"
        "From the scraped pages below, produce a concise markdown brief with these sections:\n"
        "**Overview** (2-3 sentences)\n"
        "**Key findings** (bullets, note which site each came from)\n"
        "**Suppliers / products** (if any)\n"
        "**Pricing mentions** (if any)\n"
        "**Contacts** (emails/phones found)\n"
        "**Recommended next steps** (2-4 bullets)\n\n"
        f"SCRAPED CONTENT:\n{context}"
    )
    settings = await get_settings_doc()
    try:
        summary = await ai_helper.complete(f"research-{research_id}", AI_SUMMARY_SYSTEM, prompt, settings)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI request failed: {str(e)[:150]}")
    await db.research.update_one({"_id": ObjectId(research_id)},
                                 {"$set": {"ai_summary": summary, "ai_summary_at": now_iso()}})
    await log_action(user, "generate", "research", research_id, "AI summary")
    return {"ok": True, "ai_summary": summary}
