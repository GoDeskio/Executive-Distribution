"""Iteration 12: Audit log + SEO ping tests."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cargo-command-58.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER_EMAIL = "admin@executivedistribution.com"
SUPER_PASS = "Executive2025!"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_EMAIL, SUPER_PASS)


@pytest.fixture(scope="module")
def valid_perms(super_token):
    r = requests.get(f"{API}/permissions", headers=_h(super_token), timeout=15)
    assert r.status_code == 200
    data = r.json()
    # Endpoint may return list of strings or list of dicts
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return [p.get("key") or p.get("name") for p in data]
    return data


@pytest.fixture(scope="module")
def subadmin_no_seo(super_token):
    """Sub-admin with dashboard/crm/settings but NOT seo."""
    email = f"TEST_noseo_{uuid.uuid4().hex[:6]}@ex.com"
    payload = {
        "email": email,
        "password": "TempPass123!",
        "name": "NoSeo Sub",
        "role": "subadmin",
        "permissions": ["dashboard", "crm", "settings"],
    }
    r = requests.post(f"{API}/users", json=payload, headers=_h(super_token), timeout=15)
    assert r.status_code in (200, 201), f"Create sub-admin failed: {r.status_code} {r.text}"
    user = r.json()
    tok = _login(email, "TempPass123!")
    yield {"id": user.get("id"), "email": email, "token": tok}
    # cleanup
    requests.delete(f"{API}/users/{user.get('id')}", headers=_h(super_token), timeout=15)


@pytest.fixture(scope="module")
def subadmin_with_seo(super_token):
    """Sub-admin with seo permission."""
    email = f"TEST_seo_{uuid.uuid4().hex[:6]}@ex.com"
    payload = {
        "email": email,
        "password": "TempPass123!",
        "name": "Seo Sub",
        "role": "subadmin",
        "permissions": ["dashboard", "seo"],
    }
    r = requests.post(f"{API}/users", json=payload, headers=_h(super_token), timeout=15)
    assert r.status_code in (200, 201), f"Create seo sub-admin failed: {r.status_code} {r.text}"
    user = r.json()
    tok = _login(email, "TempPass123!")
    yield {"id": user.get("id"), "email": email, "token": tok}
    requests.delete(f"{API}/users/{user.get('id')}", headers=_h(super_token), timeout=15)


# ---------- AUDIT LOG ACCESS ----------

class TestAuditAccess:
    def test_audit_unauth_401(self):
        r = requests.get(f"{API}/audit", timeout=15)
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"

    def test_audit_subadmin_forbidden(self, subadmin_no_seo):
        r = requests.get(f"{API}/audit", headers=_h(subadmin_no_seo["token"]), timeout=15)
        assert r.status_code == 403, f"Expected 403 for sub-admin, got {r.status_code} {r.text}"

    def test_audit_subadmin_with_seo_still_forbidden(self, subadmin_with_seo):
        r = requests.get(f"{API}/audit", headers=_h(subadmin_with_seo["token"]), timeout=15)
        assert r.status_code == 403

    def test_audit_superadmin_ok(self, super_token):
        r = requests.get(f"{API}/audit", headers=_h(super_token), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


# ---------- AUDIT ENTRIES ARE WRITTEN ----------

class TestAuditEntries:
    def test_mutations_produce_audit(self, super_token):
        # Perform login (already done, but do a fresh one to guarantee event)
        _login(SUPER_EMAIL, SUPER_PASS)

        # Create + delete a client
        c_payload = {"name": "TEST_AuditClient", "email": "auditclient@test.com", "phone": "+10000"}
        rc = requests.post(f"{API}/clients", json=c_payload, headers=_h(super_token), timeout=15)
        assert rc.status_code in (200, 201), f"client create: {rc.status_code} {rc.text}"
        client_id = rc.json().get("id")

        rd = requests.delete(f"{API}/clients/{client_id}", headers=_h(super_token), timeout=15)
        assert rd.status_code in (200, 204)

        # Create a service
        svc_payload = {"title": "TEST_AuditService", "slug": f"test-audit-{uuid.uuid4().hex[:6]}",
                       "description": "audit test", "published": False}
        rs = requests.post(f"{API}/services", json=svc_payload, headers=_h(super_token), timeout=15)
        assert rs.status_code in (200, 201), f"service create: {rs.status_code} {rs.text}"
        service_id = rs.json().get("id")

        # Create a document
        doc_payload = {"title": "TEST_AuditDoc", "type": "invoice", "content": "hello"}
        rdoc = requests.post(f"{API}/documents", json=doc_payload, headers=_h(super_token), timeout=15)
        assert rdoc.status_code in (200, 201), f"document create: {rdoc.status_code} {rdoc.text}"
        doc_id = rdoc.json().get("id")

        time.sleep(1)  # let async writes settle

        # Fetch audit
        r = requests.get(f"{API}/audit?limit=500", headers=_h(super_token), timeout=15)
        assert r.status_code == 200
        entries = r.json()
        assert isinstance(entries, list) and len(entries) > 0

        actions_entities = {(e.get("action"), e.get("entity")) for e in entries}
        # login event
        assert any(a == "login" and e == "auth" for (a, e) in actions_entities), \
            f"missing login/auth in audit; sample: {list(actions_entities)[:20]}"
        # client create + delete
        assert any(a == "create" and e == "client" for (a, e) in actions_entities)
        assert any(a == "delete" and e == "client" for (a, e) in actions_entities)
        assert any(a == "create" and e == "service" for (a, e) in actions_entities)
        assert any(a == "create" and e == "document" for (a, e) in actions_entities)

        # Shape check on first entry
        for e in entries[:5]:
            assert "user_email" in e
            assert "action" in e
            assert "entity" in e
            assert "created_at" in e
            # no secret leakage
            assert "password_hash" not in e
            assert "password" not in e

        # cleanup service + document
        requests.delete(f"{API}/services/{service_id}", headers=_h(super_token), timeout=15)
        requests.delete(f"{API}/documents/{doc_id}", headers=_h(super_token), timeout=15)

    def test_audit_filter_entity(self, super_token):
        r = requests.get(f"{API}/audit?entity=client&limit=100", headers=_h(super_token), timeout=15)
        assert r.status_code == 200
        entries = r.json()
        assert all(e.get("entity") == "client" for e in entries), \
            f"filter entity=client returned other entities"

    def test_audit_filter_action(self, super_token):
        r = requests.get(f"{API}/audit?action=delete&limit=100", headers=_h(super_token), timeout=15)
        assert r.status_code == 200
        entries = r.json()
        assert all(e.get("action") == "delete" for e in entries)


# ---------- SEO PING ----------

class TestSeoPing:
    def test_seo_ping_subadmin_no_perm_403(self, subadmin_no_seo):
        r = requests.post(f"{API}/seo/ping", headers=_h(subadmin_no_seo["token"]), timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"

    def test_seo_ping_subadmin_with_perm_200(self, subadmin_with_seo):
        r = requests.post(f"{API}/seo/ping", headers=_h(subadmin_with_seo["token"]), timeout=30)
        assert r.status_code == 200, f"expected 200 for seo sub-admin, got {r.status_code} {r.text}"
        data = r.json()
        assert "base_url" in data and "results" in data
        results = data["results"]
        assert "google" in results and "bing" in results and "indexnow" in results

    def test_seo_ping_superadmin_200_shape(self, super_token):
        r = requests.post(f"{API}/seo/ping", headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "base_url" in data
        results = data["results"]
        assert set(["google", "bing", "indexnow"]).issubset(results.keys())
        # With no key configured, indexnow should be skipped
        # (may already be configured from prior tests — allow either)
        # No crash requirement: values may be int status or "error: ..." or "skipped (no key)"


# ---------- INDEXNOW KEY FILE ----------

class TestIndexNowKeyFile:
    def test_no_key_returns_404(self, super_token):
        # ensure cleared
        requests.put(f"{API}/settings", json={"indexnow_key": ""}, headers=_h(super_token), timeout=15)
        r = requests.get(f"{API}/indexnow/anything.txt", timeout=15)
        assert r.status_code == 404

    def test_configured_key_served(self, super_token):
        r = requests.put(f"{API}/settings", json={"indexnow_key": "testkey123"},
                         headers=_h(super_token), timeout=15)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/indexnow/testkey123.txt", timeout=15)
        assert r2.status_code == 200
        assert r2.text.strip() == "testkey123"
        assert "text/plain" in r2.headers.get("content-type", "")

        r3 = requests.get(f"{API}/indexnow/wrongkey.txt", timeout=15)
        assert r3.status_code == 404

        # cleanup
        requests.put(f"{API}/settings", json={"indexnow_key": ""},
                     headers=_h(super_token), timeout=15)


# ---------- SETTINGS SANITIZATION ----------

class TestSettingsSanitization:
    def test_secrets_not_leaked_and_seo_fields(self, super_token):
        # set a bunch
        payload = {
            "search_engine_ping_enabled": True,
            "indexnow_key": "temp_check_key",
        }
        r = requests.put(f"{API}/settings", json=payload, headers=_h(super_token), timeout=15)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/settings", timeout=15)
        assert r2.status_code == 200
        s = r2.json()
        # no secrets
        for k in ("ai_own_key", "email_api_key", "slack_webhook_url", "stytch_secret"):
            assert k not in s, f"leaked secret field: {k}"
        # has_* booleans
        for k in ("has_own_key", "has_email_key", "has_slack_webhook", "has_stytch_secret"):
            assert k in s, f"missing has_* boolean: {k}"
            assert isinstance(s[k], bool)
        # writable seo fields readable
        assert s.get("search_engine_ping_enabled") is True
        assert s.get("indexnow_key") == "temp_check_key"

        # reset
        requests.put(f"{API}/settings",
                     json={"search_engine_ping_enabled": False, "indexnow_key": ""},
                     headers=_h(super_token), timeout=15)


# ---------- REGRESSION ----------

class TestRegression:
    def test_superadmin_login_works(self):
        tok = _login(SUPER_EMAIL, SUPER_PASS)
        assert tok

    def test_rbac_clients_gated(self, subadmin_no_seo, super_token):
        # subadmin_no_seo has crm — should be 200
        r = requests.get(f"{API}/clients", headers=_h(subadmin_no_seo["token"]), timeout=15)
        assert r.status_code == 200

        # create a sub-admin WITHOUT crm to check 403
        email = f"TEST_nocrm_{uuid.uuid4().hex[:6]}@ex.com"
        rc = requests.post(f"{API}/users", json={
            "email": email, "password": "TempPass123!", "name": "n",
            "role": "subadmin", "permissions": ["dashboard"],
        }, headers=_h(super_token), timeout=15)
        assert rc.status_code in (200, 201)
        uid = rc.json().get("id")
        try:
            tok = _login(email, "TempPass123!")
            r2 = requests.get(f"{API}/clients", headers=_h(tok), timeout=15)
            assert r2.status_code == 403, f"expected 403, got {r2.status_code}"
        finally:
            requests.delete(f"{API}/users/{uid}", headers=_h(super_token), timeout=15)

    def test_sitemap_and_robots(self):
        r = requests.get(f"{API}/sitemap.xml", timeout=15)
        assert r.status_code == 200
        assert "<urlset" in r.text and "<url>" in r.text
        r2 = requests.get(f"{API}/robots.txt", timeout=15)
        assert r2.status_code == 200
        assert "User-agent" in r2.text and "Sitemap:" in r2.text
