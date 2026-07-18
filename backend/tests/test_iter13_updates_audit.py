"""Iteration 13 tests: Update Checker/Notifier + Audit CSV export + persistence regressions."""
import os
import uuid
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL not configured"
    return v.rstrip("/")

BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

SUPER_EMAIL = "admin@executivedistribution.com"
SUPER_PASS = "Executive2025!"


# -------- Fixtures --------
@pytest.fixture(scope="module")
def super_token():
    r = requests.post(f"{API}/auth/login", json={"email": SUPER_EMAIL, "password": SUPER_PASS}, timeout=15)
    assert r.status_code == 200, f"Superadmin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_headers(super_token):
    return {"Authorization": f"Bearer {super_token}"}


@pytest.fixture(scope="module")
def sub_admin(super_headers):
    email = f"TEST_subadmin_{uuid.uuid4().hex[:8]}@example.com"
    password = "SubAdmin!2025"
    payload = {
        "email": email,
        "name": "Test SubAdmin",
        "password": password,
        "role": "subadmin",
        "permissions": ["settings", "seo"],
        "active": True,
    }
    r = requests.post(f"{API}/users", json=payload, headers=super_headers, timeout=15)
    assert r.status_code in (200, 201), f"Sub-admin create failed: {r.status_code} {r.text}"
    user_id = r.json().get("id") or r.json().get("_id")
    # login as sub-admin
    lr = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert lr.status_code == 200, f"Subadmin login failed: {lr.status_code} {lr.text}"
    token = lr.json()["token"]
    yield {"id": user_id, "email": email, "token": token,
           "headers": {"Authorization": f"Bearer {token}"}}
    # teardown
    if user_id:
        requests.delete(f"{API}/users/{user_id}", headers=super_headers, timeout=15)


@pytest.fixture(scope="module")
def prior_tagline(super_headers):
    r = requests.get(f"{API}/settings", timeout=15)
    prior = r.json().get("tagline", "") if r.status_code == 200 else ""
    yield prior
    # restore
    requests.put(f"{API}/settings", json={"tagline": prior}, headers=super_headers, timeout=15)


# -------- Auth / me --------
class TestAuth:
    def test_superadmin_login_and_me(self, super_headers):
        r = requests.get(f"{API}/auth/me", headers=super_headers, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("role") == "superadmin"
        assert data.get("email") == SUPER_EMAIL


# -------- RBAC on update endpoints --------
class TestUpdatesRBAC:
    def test_updates_status_unauth_401(self):
        r = requests.get(f"{API}/updates/status", timeout=15)
        assert r.status_code in (401, 403)

    def test_updates_check_unauth_401(self):
        r = requests.post(f"{API}/updates/check", timeout=15)
        assert r.status_code in (401, 403)

    def test_subadmin_forbidden_status(self, sub_admin):
        r = requests.get(f"{API}/updates/status", headers=sub_admin["headers"], timeout=15)
        assert r.status_code == 403, f"Expected 403, got {r.status_code} {r.text}"

    def test_subadmin_forbidden_check(self, sub_admin):
        r = requests.post(f"{API}/updates/check", headers=sub_admin["headers"], timeout=15)
        assert r.status_code == 403

    def test_subadmin_forbidden_mark_current(self, sub_admin):
        r = requests.post(f"{API}/updates/mark-current", headers=sub_admin["headers"], timeout=15)
        assert r.status_code == 403

    def test_subadmin_forbidden_apply(self, sub_admin):
        r = requests.post(f"{API}/updates/apply", headers=sub_admin["headers"], timeout=15)
        assert r.status_code == 403


# -------- Update flow (superadmin, graceful) --------
class TestUpdatesFlow:
    def test_configure_repo_and_check(self, super_headers):
        payload = {
            "update_repo_url": "https://github.com/GoDeskio/Executive-Distribution.git",
            "update_branch": "main",
        }
        r = requests.put(f"{API}/settings", json=payload, headers=super_headers, timeout=20)
        assert r.status_code == 200

        # POST /updates/check — must return 200 even if GitHub errors (repo empty / network)
        r2 = requests.post(f"{API}/updates/check", headers=super_headers, timeout=30)
        assert r2.status_code == 200, f"Expected graceful 200, got {r2.status_code} {r2.text}"
        body = r2.json()
        assert isinstance(body, dict)
        # accept either an error field, or a good latest lookup
        assert "configured" in body or "error" in body or "latest_version" in body

    def test_settings_hides_update_token(self, super_headers):
        # Set a token
        requests.put(f"{API}/settings", json={"update_token": "ghp_TESTTOKEN_do_not_use_1234"},
                     headers=super_headers, timeout=15)
        # GET /settings should not include raw update_token
        r = requests.get(f"{API}/settings", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "update_token" not in data, "update_token must not be exposed"
        assert data.get("has_update_token") is True
        # cleanup token
        requests.put(f"{API}/settings", json={"update_token": ""},
                     headers=super_headers, timeout=15)

    def test_updates_status_shape(self, super_headers):
        r = requests.get(f"{API}/updates/status", headers=super_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        for key in ("configured", "repo_url", "branch", "current_version",
                    "latest_version", "update_available", "last_checked", "last_error"):
            assert key in d, f"missing key {key}"
        assert d["configured"] is True
        assert "update_token" not in d

    def test_updates_apply_managed(self, super_headers):
        # Ensure no UPDATE_SCRIPT env → should return managed guidance
        r = requests.post(f"{API}/updates/apply", headers=super_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is False
        assert d.get("managed") is True
        assert "message" in d

    def test_mark_current_when_no_latest(self, super_headers):
        # Repo is empty → likely no latest_version. Accept either graceful ok:false or ok:true.
        r = requests.post(f"{API}/updates/mark-current", headers=super_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "ok" in d
        if d["ok"] is False:
            assert "error" in d


# -------- Audit --------
class TestAudit:
    def test_audit_list_superadmin(self, super_headers):
        r = requests.get(f"{API}/audit?limit=25", headers=super_headers, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_audit_list_filters(self, super_headers):
        r = requests.get(f"{API}/audit", headers=super_headers,
                         params={"entity": "settings", "limit": 20}, timeout=15)
        assert r.status_code == 200
        docs = r.json()
        assert isinstance(docs, list)
        for d in docs:
            assert d.get("entity") == "settings"

    def test_audit_csv_superadmin(self, super_headers):
        r = requests.get(f"{API}/audit/export.csv", headers=super_headers, timeout=20)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("text/csv")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        first_line = r.text.splitlines()[0] if r.text else ""
        assert first_line == "created_at,user_email,user_name,action,entity,entity_id,detail"

    def test_audit_csv_forbidden_subadmin(self, sub_admin):
        r = requests.get(f"{API}/audit/export.csv", headers=sub_admin["headers"], timeout=15)
        assert r.status_code == 403

    def test_audit_list_forbidden_subadmin(self, sub_admin):
        r = requests.get(f"{API}/audit", headers=sub_admin["headers"], timeout=15)
        assert r.status_code == 403


# -------- Persistence regression --------
class TestPersistence:
    def test_settings_persist_tagline(self, super_headers, prior_tagline):
        marker = f"PERSIST-TEST-{uuid.uuid4().hex[:6]}"
        r = requests.put(f"{API}/settings", json={"tagline": marker},
                         headers=super_headers, timeout=15)
        assert r.status_code == 200
        r2 = requests.get(f"{API}/settings", timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("tagline") == marker


# -------- General regressions --------
class TestRegressions:
    def test_subadmin_no_crm_forbidden(self, sub_admin):
        r = requests.get(f"{API}/clients", headers=sub_admin["headers"], timeout=15)
        assert r.status_code == 403

    def test_sitemap(self):
        r = requests.get(f"{API}/sitemap.xml", timeout=15)
        assert r.status_code == 200
        assert "<urlset" in r.text

    def test_robots(self):
        r = requests.get(f"{API}/robots.txt", timeout=15)
        assert r.status_code == 200
        assert "User-agent:" in r.text

    def test_seo_ping_superadmin(self, super_headers):
        r = requests.post(f"{API}/seo/ping", headers=super_headers, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "base_url" in d
        assert "results" in d
