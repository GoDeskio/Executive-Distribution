import asyncio
import requests

from core.db import db
from core.utils import logger

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"


async def build_urls(base_url: str):
    base = base_url.rstrip("/")
    urls = [f"{base}/"]
    services = await db.services.find({"published": True}, {"slug": 1}).to_list(500)
    for sv in services:
        if sv.get("slug"):
            urls.append(f"{base}/services/{sv['slug']}")
    return urls


def ping_search_engines(base_url: str, urls, indexnow_key: str = ""):
    """Synchronous — run inside asyncio.to_thread. Returns per-target status."""
    results = {}
    base = base_url.rstrip("/")
    host = base.split("://")[-1].split("/")[0]
    sitemap = f"{base}/api/sitemap.xml"

    # Legacy sitemap ping (Google & Bing have deprecated these; kept best-effort)
    for name, url in [("google", f"https://www.google.com/ping?sitemap={sitemap}"),
                      ("bing", f"https://www.bing.com/ping?sitemap={sitemap}")]:
        try:
            r = requests.get(url, timeout=8)
            results[name] = r.status_code
        except Exception as e:
            results[name] = f"error: {str(e)[:60]}"

    # IndexNow (current standard, used by Bing/Yandex/Seznam) — needs a key
    if indexnow_key and urls:
        try:
            payload = {
                "host": host,
                "key": indexnow_key,
                "keyLocation": f"{base}/api/indexnow/{indexnow_key}.txt",
                "urlList": list(urls)[:100],
            }
            r = requests.post(INDEXNOW_ENDPOINT, json=payload, timeout=10)
            results["indexnow"] = r.status_code
        except Exception as e:
            results["indexnow"] = f"error: {str(e)[:60]}"
    else:
        results["indexnow"] = "skipped (no key)"
    return results


async def ping_now(base_url: str, indexnow_key: str = ""):
    urls = await build_urls(base_url)
    return await asyncio.to_thread(ping_search_engines, base_url, urls, indexnow_key)


async def maybe_autoping():
    """Fire-and-forget ping after content changes, if enabled and a Site URL is set."""
    from core.settings_store import get_settings_doc
    try:
        s = await get_settings_doc()
        if not s.get("search_engine_ping_enabled"):
            return
        base = (s.get("site_url") or "").strip().rstrip("/")
        if not base:
            return
        urls = await build_urls(base)
        key = (s.get("indexnow_key") or "").strip()
        asyncio.create_task(asyncio.to_thread(ping_search_engines, base, urls, key))
    except Exception as e:
        logger.warning(f"autoping failed: {e}")
