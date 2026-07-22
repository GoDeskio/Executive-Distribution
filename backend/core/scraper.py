import re
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from core.utils import logger

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
MAX_BYTES = 3_500_000
MAX_LINKS = 200
MAX_SNIPPETS_PER_KW = 5
TEXT_EXCERPT = 3000

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?){2,4}\d{2,4})")


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _robots_allows(url: str) -> bool:
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = RobotFileParser()
        rp.set_url(urljoin(base, "/robots.txt"))
        rp.read()
        return rp.can_fetch(UA, url)
    except Exception:
        return True  # if robots can't be read, don't block


def _http_get(url: str):
    last_err = None
    for attempt in range(3):
        try:
            resp = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"},
                                timeout=25, stream=True)
            if resp.status_code in (403, 429, 503):
                last_err = f"HTTP {resp.status_code}"
                time.sleep(0.8 * (attempt + 1))
                continue
            resp.raise_for_status()
            content = resp.raw.read(MAX_BYTES, decode_content=True)
            html = content.decode(resp.encoding or "utf-8", errors="ignore")
            return html, None
        except Exception as e:
            last_err = str(e)[:150]
            time.sleep(0.6 * (attempt + 1))
    return None, last_err or "request failed"


def _scraperapi_get(url: str, api_key: str):
    try:
        resp = requests.get("https://api.scraperapi.com",
                            params={"api_key": api_key, "url": url, "render": "true"}, timeout=70)
        if resp.status_code != 200:
            return None, f"ScraperAPI HTTP {resp.status_code}"
        return resp.text, None
    except Exception as e:
        return None, str(e)[:150]


def _parse(html: str, base_url: str, keywords: list):
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    title = _normalize_ws(soup.title.get_text()) if soup.title else ""
    meta_desc = ""
    for sel in [("meta", {"name": "description"}), ("meta", {"property": "og:description"})]:
        tag = soup.find(*sel)
        if tag and tag.get("content"):
            meta_desc = _normalize_ws(tag["content"])
            break

    for t in soup(["script", "style", "noscript", "template"]):
        t.decompose()
    full_text = _normalize_ws(soup.get_text(" "))

    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"].strip())
        if href.startswith("http") and href not in seen:
            seen.add(href)
            links.append({"url": href, "text": _normalize_ws(a.get_text())[:120]})
        if len(links) >= MAX_LINKS:
            break

    emails = sorted(set(EMAIL_RE.findall(html)))[:50]
    phones = sorted({_normalize_ws(p) for p in PHONE_RE.findall(full_text)
                     if len(re.sub(r"\D", "", p)) >= 7})[:30]

    matches = []
    low = full_text.lower()
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        klow = kw.lower()
        count = low.count(klow)
        snippets = []
        if count:
            start = 0
            while len(snippets) < MAX_SNIPPETS_PER_KW:
                idx = low.find(klow, start)
                if idx == -1:
                    break
                a = max(0, idx - 90)
                b = min(len(full_text), idx + len(kw) + 90)
                snippets.append(("…" if a > 0 else "") + full_text[a:b].strip() + ("…" if b < len(full_text) else ""))
                start = idx + len(kw)
        matches.append({"keyword": kw, "count": count, "snippets": snippets})

    return {
        "title": title,
        "meta_description": meta_desc,
        "text_excerpt": full_text[:TEXT_EXCERPT],
        "word_count": len(full_text.split()),
        "links": links,
        "link_count": len(links),
        "emails": emails,
        "phones": phones,
        "keyword_matches": matches,
        "total_matches": sum(m["count"] for m in matches),
    }


def scrape_url(url: str, keywords: list, render: bool, api_key: str, respect_robots: bool = True):
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    result = {"url": url, "status": "ok", "engine": "http", "error": None}

    if respect_robots and not _robots_allows(url):
        result.update(status="blocked_by_robots", error="Disallowed by the site's robots.txt")
        return result

    if render:
        if not api_key:
            result.update(status="error", error="JavaScript rendering requires a ScraperAPI key (add it in Settings).")
            return result
        html, err = _scraperapi_get(url, api_key)
        result["engine"] = "scraperapi"
    else:
        html, err = _http_get(url)

    if err or not html:
        result.update(status="error", error=err or "no content")
        return result

    try:
        result.update(_parse(html, url, keywords))
    except Exception as e:
        logger.warning(f"parse error {url}: {e}")
        result.update(status="error", error=f"parse failed: {str(e)[:120]}")
    return result
