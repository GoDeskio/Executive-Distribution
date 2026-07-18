"""
Post-refactor regression suite for Iteration 11.
Verifies that the modular split (core/ + routers/) preserved all endpoint
paths, request/response shapes, and permission gating.
"""
import io
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cargo-command-58.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER_EMAIL = "admin@executivedistribution.com"
SUPER_PASSWORD = "Executive2025!"

ALL_PERMS = ["dashboard", "ai", "documents", "services", "crm", "storage", "seo", "settings", "search"]


# ------------------------- fixtures -------------------------
@pytest.fixture(scope="session")
def super_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": SUPER_EMAIL, "password": SUPER_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def super_headers(super_token):
    return {"Authorization": f"Bearer {super_token}"}


def _make_subadmin(super_headers, perms, password="TestPass123!"):
    email = f"TEST_sub_{uuid.uuid4().hex[:8]}@exd.com"
    r = requests.post(f"{API}/users", headers=super_headers,
                      json={"email": email, "password": password, "name": "Test Sub",
                            "permissions": perms}, timeout=30)
    assert r.status_code == 200, r.text
    uid = r.json()["id"]
    tr = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert tr.status_code == 200, tr.text
    return uid, tr.json()["token"], email, password


def _delete_user(super_headers, uid):
    try:
        requests.delete(f"{API}/users/{uid}", headers=super_headers, timeout=15)
    except Exception:
        pass


# ------------------------- auth -------------------------
class TestAuth:
    def test_login_returns_token_and_user(self, super_token):
        assert isinstance(super_token, str) and len(super_token) > 20

    def test_me_returns_superadmin_with_perms(self, super_headers):
        r = requests.get(f"{API}/auth/me", headers=super_headers, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert j["role"] == "superadmin"
        assert j["email"] == SUPER_EMAIL
        assert set(ALL_PERMS).issubset(set(j.get("permissions") or []))

    def test_me_unauth(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_profile_update_name(self, super_headers):
        r = requests.get(f"{API}/auth/me", headers=super_headers, timeout=10)
        original = r.json().get("name")
        new_name = f"Executive Admin {uuid.uuid4().hex[:4]}"
        r = requests.put(f"{API}/auth/profile", headers=super_headers,
                         json={"name": new_name}, timeout=15)
        assert r.status_code == 200
        assert r.json()["name"] == new_name
        # verify via /me
        r2 = requests.get(f"{API}/auth/me", headers=super_headers, timeout=10)
        assert r2.json()["name"] == new_name
        # restore
        requests.put(f"{API}/auth/profile", headers=super_headers,
                     json={"name": original or "Executive Admin"}, timeout=15)


# ------------------------- lockout -------------------------
class TestLockout:
    def test_lockout_on_throwaway_subadmin(self, super_headers):
        # set lockout to small: 3 attempts / 1 min
        settings_before = requests.get(f"{API}/settings", timeout=10).json()
        requests.put(f"{API}/settings", headers=super_headers,
                     json={"lockout_max_attempts": 3, "lockout_minutes": 1}, timeout=15)

        uid, _tok, email, password = _make_subadmin(super_headers, ["dashboard"])
        try:
            # 3 wrong attempts
            statuses = []
            for _ in range(3):
                r = requests.post(f"{API}/auth/login",
                                  json={"email": email, "password": "wrong-pw"}, timeout=15)
                statuses.append(r.status_code)
            # third should be 429 (locked on threshold reached)
            assert 429 in statuses, f"Expected 429 in {statuses}"

            # correct password should now be blocked
            r = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": password}, timeout=15)
            assert r.status_code == 429, f"Expected 429 with correct pw during lock, got {r.status_code} {r.text}"
        finally:
            _delete_user(super_headers, uid)
            # restore lockout defaults
            requests.put(f"{API}/settings", headers=super_headers,
                         json={"lockout_max_attempts": int(settings_before.get("lockout_max_attempts", 5) or 5),
                               "lockout_minutes": int(settings_before.get("lockout_minutes", 15) or 15)},
                         timeout=15)


# ------------------------- services -------------------------
class TestServices:
    def test_public_list(self):
        r = requests.get(f"{API}/services", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_all_flag(self, super_headers):
        r = requests.get(f"{API}/services?all=true", timeout=15)
        assert r.status_code == 200

    def test_get_by_slug(self):
        lst = requests.get(f"{API}/services", timeout=15).json()
        if not lst:
            pytest.skip("no services seeded")
        slug = lst[0]["slug"]
        r = requests.get(f"{API}/services/{slug}", timeout=15)
        assert r.status_code == 200
        assert r.json()["slug"] == slug

    def test_crud_gated(self, super_headers):
        # unauth create -> 401
        r = requests.post(f"{API}/services", json={"title": "TEST X"}, timeout=15)
        assert r.status_code == 401

        # super create/update/delete
        r = requests.post(f"{API}/services", headers=super_headers,
                          json={"title": f"TEST_svc_{uuid.uuid4().hex[:6]}",
                                "short_description": "x"}, timeout=15)
        assert r.status_code == 200
        sid = r.json()["id"]
        try:
            r = requests.put(f"{API}/services/{sid}", headers=super_headers,
                             json={"title": r.json()["title"], "short_description": "y"}, timeout=15)
            assert r.status_code == 200
            assert r.json()["short_description"] == "y"
        finally:
            requests.delete(f"{API}/services/{sid}", headers=super_headers, timeout=15)


# ------------------------- clients + portal -------------------------
class TestClientsPortal:
    def test_clients_crud_and_portal(self, super_headers):
        # unauth -> 401
        r = requests.get(f"{API}/clients", timeout=10)
        assert r.status_code == 401

        # create
        r = requests.post(f"{API}/clients", headers=super_headers,
                          json={"name": f"TEST_client_{uuid.uuid4().hex[:6]}", "email": "t@t.com"}, timeout=15)
        assert r.status_code == 200
        cid = r.json()["id"]
        try:
            # get docs (empty ok)
            r = requests.get(f"{API}/clients/{cid}/documents", headers=super_headers, timeout=15)
            assert r.status_code == 200
            assert isinstance(r.json(), list)

            # generate portal token
            r = requests.post(f"{API}/clients/{cid}/portal-token", headers=super_headers,
                              json={"expires_days": 7}, timeout=15)
            assert r.status_code == 200
            token = r.json()["token"]

            # public portal
            r = requests.get(f"{API}/portal/{token}", timeout=15)
            assert r.status_code == 200
            j = r.json()
            assert "client" in j and "company" in j and "documents" in j

            # revoke
            r = requests.delete(f"{API}/clients/{cid}/portal-token", headers=super_headers, timeout=15)
            assert r.status_code == 200
            # portal 404 after revoke
            r = requests.get(f"{API}/portal/{token}", timeout=15)
            assert r.status_code == 404
        finally:
            requests.delete(f"{API}/clients/{cid}", headers=super_headers, timeout=15)


# ------------------------- portal approve -------------------------
class TestPortalApprove:
    def test_approve_creates_notification(self, super_headers):
        # create a client
        r = requests.post(f"{API}/clients", headers=super_headers,
                          json={"name": f"TEST_papprove_{uuid.uuid4().hex[:6]}"}, timeout=15)
        cid = r.json()["id"]
        # portal token
        tr = requests.post(f"{API}/clients/{cid}/portal-token", headers=super_headers,
                           json={"expires_days": 1}, timeout=15)
        token = tr.json()["token"]
        # create a document linked to that client + shared, and generate to get pdf_file_id
        dr = requests.post(f"{API}/documents", headers=super_headers, json={
            "doc_type": "quote", "client_id": cid, "client_name": "T",
            "line_items": [{"item": "widget", "qty": 1, "unit_price": 10, "total": 10}],
            "grand_total": 10, "shared": True,
        }, timeout=20)
        assert dr.status_code == 200, dr.text
        did = dr.json()["id"]
        try:
            gr = requests.post(f"{API}/documents/{did}/generate", headers=super_headers, timeout=30)
            assert gr.status_code == 200, gr.text
            assert "file_id" in gr.json()

            # portal now should show 1 shared doc
            pr = requests.get(f"{API}/portal/{token}", timeout=15)
            assert pr.status_code == 200
            docs = pr.json()["documents"]
            assert any(d["id"] == did for d in docs)

            # approve
            ar = requests.post(f"{API}/portal/{token}/approve", json={"document_id": did}, timeout=15)
            assert ar.status_code == 200
            assert ar.json()["status"] == "approved"

            # notification exists
            nr = requests.get(f"{API}/notifications", headers=super_headers, timeout=10)
            assert nr.status_code == 200
            assert any(n.get("document_id") == did for n in nr.json())
        finally:
            requests.delete(f"{API}/documents/{did}", headers=super_headers, timeout=15)
            requests.delete(f"{API}/clients/{cid}", headers=super_headers, timeout=15)


# ------------------------- documents -------------------------
class TestDocuments:
    def test_documents_gated(self):
        r = requests.get(f"{API}/documents", timeout=10)
        assert r.status_code == 401

    def test_documents_crud_and_share(self, super_headers):
        r = requests.post(f"{API}/documents", headers=super_headers, json={
            "doc_type": "quote", "client_name": "TEST",
            "line_items": [{"item": "a", "qty": 2, "unit_price": 5, "total": 10}],
            "grand_total": 10,
        }, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["number"].startswith("EXD-Q-")
        did = d["id"]
        try:
            # share toggle
            r = requests.post(f"{API}/documents/{did}/share", headers=super_headers,
                              json={"shared": False}, timeout=15)
            assert r.status_code == 200 and r.json()["shared"] is False
        finally:
            requests.delete(f"{API}/documents/{did}", headers=super_headers, timeout=15)

    def test_ai_draft_returns_structure_or_clean_error(self, super_headers):
        r = requests.post(f"{API}/documents/ai-draft", headers=super_headers,
                          json={"description": "2 laptops from China to Kenya via ocean, ~4kg each, $600 each",
                                "doc_type": "quote"}, timeout=90)
        # accept 200 with structure OR clean 4xx/502 if AI unavailable
        if r.status_code == 200:
            j = r.json()
            assert "line_items" in j
            assert "grand_total" in j
        else:
            assert r.status_code in (400, 401, 402, 422, 429, 502, 503), f"unexpected {r.status_code}: {r.text[:200]}"


# ------------------------- quotes -------------------------
class TestQuotes:
    def test_public_intake(self):
        # multipart form
        files = {"images": ("t.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")}
        data = {"name": "TEST", "email": "q@t.com", "company": "TC",
                "phone": "1", "destination": "US", "description": "d"}
        r = requests.post(f"{API}/quotes", data=data, files=files, timeout=30)
        assert r.status_code == 200
        assert "id" in r.json()

    def test_list_and_put_returns_updated(self, super_headers):
        # unauth list -> 401
        assert requests.get(f"{API}/quotes", timeout=10).status_code == 401
        # create via public
        r = requests.post(f"{API}/quotes", data={"name": "TEST_pq", "email": "pq@t.com"}, timeout=20)
        qid = r.json()["id"]
        try:
            # list
            r = requests.get(f"{API}/quotes", headers=super_headers, timeout=15)
            assert r.status_code == 200
            assert any(q["id"] == qid for q in r.json())
            # put returns updated object with echoed status
            r = requests.put(f"{API}/quotes/{qid}", headers=super_headers,
                             json={"status": "contacted", "notes": "reached out"}, timeout=15)
            assert r.status_code == 200
            j = r.json()
            assert j["status"] == "contacted"
            assert j["notes"] == "reached out"
            assert j["id"] == qid
        finally:
            r = requests.delete(f"{API}/quotes/{qid}", headers=super_headers, timeout=15)
            assert r.status_code == 200


# ------------------------- files -------------------------
class TestFiles:
    def test_upload_list_delete_and_raw(self, super_headers):
        assert requests.get(f"{API}/files", timeout=10).status_code == 401

        content = b"hello-refactor"
        files = {"file": ("t.txt", io.BytesIO(content), "text/plain")}
        data = {"category": "asset"}
        r = requests.post(f"{API}/files/upload", headers=super_headers, files=files, data=data, timeout=30)
        assert r.status_code == 200, r.text
        fid = r.json()["id"]
        try:
            # raw is public
            rr = requests.get(f"{API}/files/{fid}/raw", timeout=15)
            assert rr.status_code == 200
            assert rr.content == content
            # list
            lr = requests.get(f"{API}/files", headers=super_headers, timeout=15)
            assert lr.status_code == 200
            assert any(f["id"] == fid for f in lr.json())
        finally:
            requests.delete(f"{API}/files/{fid}", headers=super_headers, timeout=15)


# ------------------------- analytics -------------------------
class TestAnalytics:
    def test_track_public(self):
        sid = f"TEST_{uuid.uuid4().hex[:8]}"
        r = requests.post(f"{API}/track", json={"session_id": sid, "path": "/",
                                                "event_type": "pageview"}, timeout=15)
        assert r.status_code == 200

    def test_analytics_gated(self, super_headers):
        for path in ["/analytics/overview", "/analytics/timeseries", "/analytics/pages",
                     "/analytics/heatmap", "/analytics/visitors"]:
            assert requests.get(f"{API}{path}", timeout=10).status_code == 401
            r = requests.get(f"{API}{path}", headers=super_headers, timeout=20)
            assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"


# ------------------------- AI status + calculate -------------------------
class TestAIMisc:
    def test_ai_status(self, super_headers):
        r = requests.get(f"{API}/ai/status", headers=super_headers, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "provider" in j and "model" in j and "source" in j

    def test_calculate_public(self):
        r = requests.post(f"{API}/calculate", json={
            "declared_value": 100, "weight_kg": 5, "quantity": 1, "mode": "ocean"
        }, timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "breakdown" in j and "grand_total" in j and "rules_used" in j


# ------------------------- settings & SEO -------------------------
class TestSettingsSEO:
    def test_settings_sanitized(self):
        r = requests.get(f"{API}/settings", timeout=15)
        assert r.status_code == 200
        j = r.json()
        # no raw secret keys
        for k in ("ai_own_key", "email_api_key", "slack_webhook_url", "stytch_secret"):
            assert k not in j, f"raw secret {k} leaked"
        # has_* booleans present
        for k in ("has_own_key", "has_email_key", "has_slack_webhook", "has_stytch_secret"):
            assert k in j, f"missing {k}"
            assert isinstance(j[k], bool)

    def test_settings_update_gated(self):
        r = requests.put(f"{API}/settings", json={"tagline": "x"}, timeout=10)
        assert r.status_code == 401

    def test_sitemap_xml(self):
        r = requests.get(f"{API}/sitemap.xml", timeout=15)
        assert r.status_code == 200
        assert "application/xml" in r.headers.get("content-type", "")
        body = r.text
        assert body.startswith("<?xml")
        assert "<urlset" in body
        # includes at least one service URL
        assert "/services/" in body

    def test_robots(self):
        r = requests.get(f"{API}/robots.txt", timeout=15)
        assert r.status_code == 200
        assert "User-agent: *" in r.text
        assert "Sitemap:" in r.text


# ------------------------- search -------------------------
class TestSearch:
    def test_search_shape(self, super_headers):
        # unauth
        assert requests.get(f"{API}/search?q=test", timeout=10).status_code == 401
        r = requests.get(f"{API}/search?q=test", headers=super_headers, timeout=15)
        assert r.status_code == 200
        j = r.json()
        for k in ("clients", "requests", "documents"):
            assert k in j


# ------------------------- RBAC regression -------------------------
class TestRBAC:
    def test_subadmin_without_perm_gets_403(self, super_headers):
        uid, tok, email, pw = _make_subadmin(super_headers, ["dashboard"])
        h = {"Authorization": f"Bearer {tok}"}
        try:
            # crm-gated
            assert requests.get(f"{API}/clients", headers=h, timeout=10).status_code == 403
            assert requests.get(f"{API}/quotes", headers=h, timeout=10).status_code == 403
            # services POST gated
            assert requests.post(f"{API}/services", headers=h,
                                 json={"title": "TEST_x"}, timeout=10).status_code == 403
            # documents
            assert requests.get(f"{API}/documents", headers=h, timeout=10).status_code == 403
            # storage
            assert requests.get(f"{API}/files", headers=h, timeout=10).status_code == 403
            # settings PUT
            assert requests.put(f"{API}/settings", headers=h,
                                json={"tagline": "x"}, timeout=10).status_code == 403
            # dashboard-gated should PASS (has dashboard)
            assert requests.get(f"{API}/analytics/overview", headers=h, timeout=15).status_code == 200
        finally:
            _delete_user(super_headers, uid)

    def test_subadmin_with_perm_succeeds(self, super_headers):
        uid, tok, email, pw = _make_subadmin(super_headers, ["crm", "documents", "storage"])
        h = {"Authorization": f"Bearer {tok}"}
        try:
            assert requests.get(f"{API}/clients", headers=h, timeout=10).status_code == 200
            assert requests.get(f"{API}/documents", headers=h, timeout=10).status_code == 200
            assert requests.get(f"{API}/files", headers=h, timeout=10).status_code == 200
            # should be forbidden on settings
            assert requests.put(f"{API}/settings", headers=h,
                                json={"tagline": "x"}, timeout=10).status_code == 403
        finally:
            _delete_user(super_headers, uid)
