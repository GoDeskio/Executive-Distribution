import re
import requests

from core.db import db
from core.utils import now_iso, logger


def parse_repo(url: str):
    """Accepts https://github.com/owner/repo(.git) or owner/repo -> (owner, repo)."""
    if not url:
        return None, None
    u = url.strip().rstrip("/")
    u = re.sub(r"\.git$", "", u)
    m = re.search(r"github\.com[/:]([^/]+)/([^/]+)$", u)
    if m:
        return m.group(1), m.group(2)
    parts = u.split("/")
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def _headers(token: str):
    h = {"Accept": "application/vnd.github+json", "User-Agent": "ExecutiveDistribution-Updater"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def fetch_latest(owner: str, repo: str, branch: str, token: str):
    """Synchronous GitHub lookup. Prefers a published release, falls back to latest commit."""
    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = _headers(token)
    # Try latest release first
    try:
        r = requests.get(f"{base}/releases/latest", headers=headers, timeout=12)
        if r.status_code == 200:
            d = r.json()
            return {"version": d.get("tag_name") or d.get("name"), "kind": "release",
                    "notes": (d.get("body") or "")[:1000], "url": d.get("html_url"),
                    "date": d.get("published_at")}
    except Exception as e:
        logger.warning(f"release lookup failed: {e}")
    # Fall back to latest commit on branch
    r = requests.get(f"{base}/commits/{branch or 'main'}", headers=headers, timeout=12)
    if r.status_code != 200:
        raise RuntimeError(f"GitHub API {r.status_code}: {r.json().get('message', '') if r.headers.get('content-type','').startswith('application/json') else r.text[:120]}")
    d = r.json()
    commit = d.get("commit", {})
    return {"version": (d.get("sha") or "")[:12], "kind": "commit",
            "notes": (commit.get("message") or "")[:1000],
            "url": d.get("html_url"),
            "date": (commit.get("author") or {}).get("date")}


async def run_check(settings: dict):
    """Live check against GitHub; persists the cached result into settings; returns status dict."""
    import asyncio
    repo_url = (settings.get("update_repo_url") or "").strip()
    if not repo_url:
        return {"configured": False, "error": "No GitHub repository configured."}
    owner, repo = parse_repo(repo_url)
    if not owner or not repo:
        return {"configured": True, "error": "Could not parse the repository URL. Use https://github.com/owner/repo."}
    branch = (settings.get("update_branch") or "main").strip()
    token = (settings.get("update_token") or "").strip()
    try:
        latest = await asyncio.to_thread(fetch_latest, owner, repo, branch, token)
    except Exception as e:
        err = str(e)[:200]
        await db.settings.update_one({"_id": "site"}, {"$set": {"update_last_checked": now_iso(), "update_last_error": err}})
        return {"configured": True, "error": err}

    current = (settings.get("update_current_version") or "").strip()
    update_available = bool(latest["version"]) and (latest["version"] != current)
    cache = {
        "update_latest_version": latest["version"],
        "update_latest_kind": latest["kind"],
        "update_latest_notes": latest["notes"],
        "update_latest_url": latest["url"],
        "update_latest_date": latest["date"],
        "update_available": update_available,
        "update_last_checked": now_iso(),
        "update_last_error": "",
    }
    await db.settings.update_one({"_id": "site"}, {"$set": cache}, upsert=True)

    if update_available:
        try:
            existing = await db.notifications.find_one({"type": "update_available", "version": latest["version"]})
            if not existing:
                await db.notifications.insert_one({
                    "type": "update_available", "version": latest["version"],
                    "document_number": latest["version"], "client_name": "System",
                    "read": False, "created_at": now_iso(),
                })
        except Exception:
            pass

    return {"configured": True, "owner": owner, "repo": repo, "branch": branch,
            "current_version": current, **cache}


def status_from_settings(settings: dict):
    return {
        "configured": bool((settings.get("update_repo_url") or "").strip()),
        "repo_url": settings.get("update_repo_url") or "",
        "branch": settings.get("update_branch") or "main",
        "auto_check": bool(settings.get("update_auto_check", True)),
        "auto_apply": bool(settings.get("update_auto_apply", False)),
        "current_version": settings.get("update_current_version") or "",
        "latest_version": settings.get("update_latest_version") or "",
        "latest_kind": settings.get("update_latest_kind") or "",
        "latest_notes": settings.get("update_latest_notes") or "",
        "latest_url": settings.get("update_latest_url") or "",
        "latest_date": settings.get("update_latest_date") or "",
        "update_available": bool(settings.get("update_available", False)),
        "last_checked": settings.get("update_last_checked") or "",
        "last_error": settings.get("update_last_error") or "",
    }
