"""Iteration 15 - Research (web scraping) tab tests."""
import os
import time
import pytest
import requests

def _load_env():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return os.environ.get("REACT_APP_BACKEND_URL", "")

BASE_URL = _load_env().rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not found"
API = f"{BASE_URL}/api"

SUPER_EMAIL = "admin@executivedistribution.com"
SUPER_PASS = "Executive2025!"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_EMAIL, SUPER_PASS)


@pytest.fixture(scope="module")
def sub_no_perm(super_token):
    email = f"TEST_sub_noperm_{int(time.time())}@ex.com"
    password = "SubTest123!"
    r = requests.post(f"{API}/users", headers=_h(super_token),
                      json={"email": email, "password": password, "name": "NoPerm",
                            "role": "subadmin", "permissions": ["dashboard"]}, timeout=30)
    assert r.status_code in (200, 201), r.text
    user_id = r.json().get("id") or r.json().get("_id")
    token = _login(email, password)
    yield {"token": token, "id": user_id, "email": email}
    if user_id:
        requests.delete(f"{API}/users/{user_id}", headers=_h(super_token), timeout=30)


@pytest.fixture(scope="module")
def sub_with_perm(super_token):
    email = f"TEST_sub_research_{int(time.time())}@ex.com"
    password = "SubTest123!"
    r = requests.post(f"{API}/users", headers=_h(super_token),
                      json={"email": email, "password": password, "name": "Researcher",
                            "role": "subadmin", "permissions": ["research"]}, timeout=30)
    assert r.status_code in (200, 201), r.text
    user_id = r.json().get("id") or r.json().get("_id")
    token = _login(email, password)
    yield {"token": token, "id": user_id, "email": email}
    if user_id:
        requests.delete(f"{API}/users/{user_id}", headers=_h(super_token), timeout=30)


# --- Test: permission list includes 'research' ---
def test_permissions_includes_research(super_token):
    r = requests.get(f"{API}/permissions", headers=_h(super_token), timeout=30)
    assert r.status_code == 200
    data = r.json()
    perms = data if isinstance(data, list) else data.get("permissions") or data.get("all") or []
    assert "research" in perms, f"'research' not in {perms}"


# --- Test: POST /research/scrape success (superadmin) ---
def test_scrape_success_superadmin(super_token):
    r = requests.post(f"{API}/research/scrape", headers=_h(super_token),
                      json={"keywords": "example, domain",
                            "urls": ["https://example.com"],
                            "render": False}, timeout=90)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert "results" in doc and len(doc["results"]) == 1
    res0 = doc["results"][0]
    # Scraping example.com should generally succeed; if network-blocked accept error but not crash
    if res0.get("status") == "ok":
        assert res0.get("title"), "title should be non-empty"
        assert "keyword_matches" in res0
        assert isinstance(res0["keyword_matches"], list)
        assert res0.get("link_count") is not None
        assert "emails" in res0 and "phones" in res0
        assert res0.get("word_count", 0) > 0
        assert "ok_count" in doc and "total_matches" in doc
        # Verify keyword_matches structure
        km = res0["keyword_matches"]
        assert any(m["keyword"] in ("example", "domain") for m in km)
        for m in km:
            assert "count" in m and "snippets" in m
    else:
        pytest.skip(f"example.com scrape returned status={res0.get('status')} err={res0.get('error')}")
    # cleanup
    doc_id = doc.get("id") or doc.get("_id")
    if doc_id:
        requests.delete(f"{API}/research/{doc_id}", headers=_h(super_token), timeout=30)


# --- RBAC tests ---
def test_scrape_403_without_perm(sub_no_perm):
    r = requests.post(f"{API}/research/scrape", headers=_h(sub_no_perm["token"]),
                      json={"urls": ["https://example.com"]}, timeout=30)
    assert r.status_code == 403, r.status_code


def test_list_403_without_perm(sub_no_perm):
    r = requests.get(f"{API}/research", headers=_h(sub_no_perm["token"]), timeout=30)
    assert r.status_code == 403


def test_delete_403_without_perm(sub_no_perm):
    r = requests.delete(f"{API}/research/507f1f77bcf86cd799439011",
                        headers=_h(sub_no_perm["token"]), timeout=30)
    assert r.status_code == 403


def test_scrape_401_unauthenticated():
    r = requests.post(f"{API}/research/scrape", json={"urls": ["https://example.com"]}, timeout=30)
    assert r.status_code == 401


def test_list_401_unauthenticated():
    r = requests.get(f"{API}/research", timeout=30)
    assert r.status_code == 401


def test_sub_with_perm_can_use(sub_with_perm, super_token):
    # POST scrape
    r = requests.post(f"{API}/research/scrape", headers=_h(sub_with_perm["token"]),
                      json={"keywords": "example", "urls": ["https://example.com"]}, timeout=90)
    assert r.status_code == 200, r.text
    doc = r.json()
    doc_id = doc.get("id") or doc.get("_id")
    # GET list
    r2 = requests.get(f"{API}/research", headers=_h(sub_with_perm["token"]), timeout=30)
    assert r2.status_code == 200
    lst = r2.json()
    assert isinstance(lst, list)
    if len(lst) > 1:
        # newest first
        assert lst[0]["created_at"] >= lst[-1]["created_at"]
    # DELETE
    if doc_id:
        r3 = requests.delete(f"{API}/research/{doc_id}", headers=_h(sub_with_perm["token"]), timeout=30)
        assert r3.status_code == 200


# --- Empty URLs ---
def test_scrape_empty_urls_400(super_token):
    r = requests.post(f"{API}/research/scrape", headers=_h(super_token),
                      json={"keywords": "x", "urls": []}, timeout=30)
    assert r.status_code == 400


# --- Render mode without a key ---
def test_render_without_key_returns_error(super_token):
    # Ensure key is not set
    requests.put(f"{API}/settings", headers=_h(super_token),
                 json={"scraperapi_key": ""}, timeout=30)
    r = requests.post(f"{API}/research/scrape", headers=_h(super_token),
                      json={"urls": ["https://example.com"], "render": True}, timeout=60)
    assert r.status_code == 200, r.text
    doc = r.json()
    res0 = doc["results"][0]
    assert res0["status"] == "error"
    assert "scraperapi" in (res0.get("error") or "").lower() or "key" in (res0.get("error") or "").lower()
    doc_id = doc.get("id") or doc.get("_id")
    if doc_id:
        requests.delete(f"{API}/research/{doc_id}", headers=_h(super_token), timeout=30)


# --- robots.txt best-effort (no crash) ---
def test_robots_no_crash(super_token):
    r = requests.post(f"{API}/research/scrape", headers=_h(super_token),
                      json={"urls": ["https://www.google.com/search?q=test"],
                            "respect_robots": True}, timeout=90)
    assert r.status_code == 200
    doc = r.json()
    res0 = doc["results"][0]
    assert res0["status"] in ("ok", "blocked_by_robots", "error")
    doc_id = doc.get("id") or doc.get("_id")
    if doc_id:
        requests.delete(f"{API}/research/{doc_id}", headers=_h(super_token), timeout=30)


# --- Settings: scraperapi_key write-only ---
def test_settings_scraperapi_write_only(super_token):
    # Ensure clean
    requests.put(f"{API}/settings", headers=_h(super_token),
                 json={"scraperapi_key": ""}, timeout=30)
    r = requests.get(f"{API}/settings", headers=_h(super_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "scraperapi_key" not in d
    assert d.get("has_scraperapi_key") is False

    # Set key
    r2 = requests.put(f"{API}/settings", headers=_h(super_token),
                      json={"scraperapi_key": "testkey"}, timeout=30)
    assert r2.status_code == 200
    r3 = requests.get(f"{API}/settings", headers=_h(super_token), timeout=30)
    d3 = r3.json()
    assert "scraperapi_key" not in d3
    assert d3.get("has_scraperapi_key") is True

    # Reset
    r4 = requests.put(f"{API}/settings", headers=_h(super_token),
                     json={"scraperapi_key": ""}, timeout=30)
    assert r4.status_code == 200
    d4 = requests.get(f"{API}/settings", headers=_h(super_token), timeout=30).json()
    assert d4.get("has_scraperapi_key") is False


# --- Regression ---
def test_superadmin_login_works():
    t = _login(SUPER_EMAIL, SUPER_PASS)
    assert t


def test_subadmin_without_crm_403(sub_no_perm):
    r = requests.get(f"{API}/clients", headers=_h(sub_no_perm["token"]), timeout=30)
    assert r.status_code == 403


def test_sitemap_still_valid():
    r = requests.get(f"{API}/sitemap.xml", timeout=30)
    assert r.status_code == 200
    assert "<urlset" in r.text


def test_audit_superadmin_only(sub_no_perm, super_token):
    r = requests.get(f"{API}/audit", headers=_h(sub_no_perm["token"]), timeout=30)
    assert r.status_code == 403
    r2 = requests.get(f"{API}/audit", headers=_h(super_token), timeout=30)
    assert r2.status_code == 200


def test_scrape_writes_audit_entry(super_token):
    r = requests.post(f"{API}/research/scrape", headers=_h(super_token),
                      json={"keywords": "example",
                            "urls": ["https://example.com"]}, timeout=90)
    assert r.status_code == 200
    doc = r.json()
    doc_id = doc.get("id") or doc.get("_id")
    time.sleep(0.5)
    ar = requests.get(f"{API}/audit", headers=_h(super_token), timeout=30)
    assert ar.status_code == 200
    audits = ar.json() if isinstance(ar.json(), list) else ar.json().get("items", [])
    found = any((a.get("entity") == "research") for a in audits[:50])
    assert found, "no research audit entry found"
    if doc_id:
        requests.delete(f"{API}/research/{doc_id}", headers=_h(super_token), timeout=30)
