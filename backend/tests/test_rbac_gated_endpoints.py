"""RBAC tests for the 7 newly-gated endpoints (iteration 10).

Endpoints newly wrapped with require_perm(...):
 - PUT    /api/quotes/{id}         -> crm
 - DELETE /api/quotes/{id}         -> crm
 - DELETE /api/services/{id}       -> services
 - DELETE /api/documents/{id}      -> documents
 - POST   /api/files/upload        -> storage
 - GET    /api/files                -> storage
 - DELETE /api/files/{id}          -> storage

Verifies:
 1) Superadmin login + /auth/me role.
 2) Superadmin can hit each gated endpoint (NOT 403).
 3) A restricted sub-admin (only 'dashboard') gets 403 on all 7.
    (The 403 must occur BEFORE any DB mutation.)
 4) A permitted sub-admin (crm+services+storage+documents) is not 403.
 5) Cleanup: temporary sub-admins and throwaway records removed.
"""
import io
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

SUPER_EMAIL = "admin@executivedistribution.com"
SUPER_PASSWORD = "Executive2025!"

# Unique emails per run to avoid collisions with parallel/previous runs
RUN = uuid.uuid4().hex[:8]
RESTRICTED_EMAIL = f"TEST_restricted_{RUN}@exd.com"
PERMITTED_EMAIL = f"TEST_permitted_{RUN}@exd.com"
PWD = "SubPass123!"


def _login(email, password):
    return requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def super_token():
    r = _login(SUPER_EMAIL, SUPER_PASSWORD)
    assert r.status_code == 200, f"superadmin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


def _create_sub(super_token, email, perms):
    # cleanup any pre-existing
    users = requests.get(f"{API}/users", headers=_h(super_token)).json()
    for u in users:
        if u["email"] == email:
            requests.delete(f"{API}/users/{u['id']}", headers=_h(super_token))
    r = requests.post(
        f"{API}/users",
        headers=_h(super_token),
        json={"email": email, "password": PWD, "name": email, "permissions": perms},
    )
    assert r.status_code == 200, f"create sub-admin ({perms}) failed: {r.status_code} {r.text}"
    created = r.json()
    lr = _login(email, PWD)
    assert lr.status_code == 200
    return created, lr.json()["token"]


@pytest.fixture(scope="module")
def restricted_sub(super_token):
    created, token = _create_sub(super_token, RESTRICTED_EMAIL, ["dashboard"])
    yield created, token
    requests.delete(f"{API}/users/{created['id']}", headers=_h(super_token))


@pytest.fixture(scope="module")
def permitted_sub(super_token):
    created, token = _create_sub(
        super_token, PERMITTED_EMAIL, ["crm", "services", "storage", "documents", "dashboard"]
    )
    yield created, token
    requests.delete(f"{API}/users/{created['id']}", headers=_h(super_token))


@pytest.fixture(scope="module")
def throwaway_ids(super_token):
    """Create a quote, service, document, and file as superadmin. Returns their ids.
    Cleanup deletes anything still present at end."""
    h = _h(super_token)
    ids = {}

    # QUOTE via public form endpoint
    r = requests.post(
        f"{API}/quotes",
        data={
            "name": "TEST_RBAC",
            "email": "rbac@test.com",
            "company": "TEST",
            "phone": "",
            "destination": "US",
            "description": "test",
        },
        timeout=20,
    )
    assert r.status_code == 200, f"create quote: {r.status_code} {r.text}"
    ids["quote"] = r.json()["id"]

    # SERVICE
    r = requests.post(
        f"{API}/services",
        headers=h,
        json={"title": f"TEST RBAC {RUN}", "short_description": "x", "full_description": "y"},
        timeout=20,
    )
    assert r.status_code == 200, f"create service: {r.status_code} {r.text}"
    ids["service"] = r.json()["id"]

    # DOCUMENT
    r = requests.post(
        f"{API}/documents",
        headers=h,
        json={"doc_type": "quote", "client_name": "TEST RBAC", "line_items": []},
        timeout=20,
    )
    assert r.status_code == 200, f"create document: {r.status_code} {r.text}"
    ids["document"] = r.json()["id"]

    # FILE  (upload as super)
    files = {"file": ("test.txt", io.BytesIO(b"hello rbac"), "text/plain")}
    r = requests.post(
        f"{API}/files/upload",
        headers=h,
        data={"category": "asset", "client_id": ""},
        files=files,
        timeout=30,
    )
    assert r.status_code == 200, f"upload file: {r.status_code} {r.text}"
    ids["file"] = r.json()["id"]

    yield ids

    # teardown: try delete each; ignore errors
    for path, key in [
        ("quotes", "quote"),
        ("services", "service"),
        ("documents", "document"),
        ("files", "file"),
    ]:
        try:
            requests.delete(f"{API}/{path}/{ids[key]}", headers=h, timeout=15)
        except Exception:
            pass


# ---------- Tests ----------
class TestSuperadminBasics:
    def test_super_login_and_me(self, super_token):
        r = requests.get(f"{API}/auth/me", headers=_h(super_token))
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "superadmin"
        assert d["email"] == SUPER_EMAIL


class TestSuperadminHitsGatedEndpoints:
    """Superadmin bypasses require_perm regardless of permissions list."""

    def test_super_put_quote(self, super_token):
        # Create an isolated quote for this test to avoid xdist ordering races
        # with the shared throwaway quote (which other tests may delete).
        cr = requests.post(f"{API}/quotes", data={"name": "PUT-ISO", "email": "put-iso@exd.com"})
        assert cr.status_code == 200, cr.text
        qid = cr.json()["id"]
        try:
            r = requests.put(
                f"{API}/quotes/{qid}",
                headers=_h(super_token),
                json={"status": "in_review", "notes": "checked"},
            )
            assert r.status_code == 200, r.text
            assert r.json().get("status") == "in_review"
        finally:
            requests.delete(f"{API}/quotes/{qid}", headers=_h(super_token))

    def test_super_list_files(self, super_token):
        r = requests.get(f"{API}/files", headers=_h(super_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_super_upload_file(self, super_token):
        files = {"file": ("s.txt", io.BytesIO(b"super"), "text/plain")}
        r = requests.post(
            f"{API}/files/upload",
            headers=_h(super_token),
            data={"category": "asset"},
            files=files,
        )
        assert r.status_code == 200
        fid = r.json()["id"]
        # cleanup
        requests.delete(f"{API}/files/{fid}", headers=_h(super_token))

    # deletes are exercised indirectly via throwaway_ids teardown; verify explicitly:
    def test_super_can_delete_created_records(self, super_token):
        h = _h(super_token)
        # quote
        rq = requests.post(
            f"{API}/quotes",
            data={"name": "TS", "email": "t@t.com", "description": "d"},
            timeout=15,
        )
        qid = rq.json()["id"]
        assert requests.delete(f"{API}/quotes/{qid}", headers=h).status_code == 200
        # service
        rs = requests.post(
            f"{API}/services",
            headers=h,
            json={"title": f"TEST SUPER DEL {RUN}"},
        )
        sid = rs.json()["id"]
        assert requests.delete(f"{API}/services/{sid}", headers=h).status_code == 200
        # document
        rd = requests.post(
            f"{API}/documents",
            headers=h,
            json={"doc_type": "quote", "client_name": "TEST", "line_items": []},
        )
        did = rd.json()["id"]
        assert requests.delete(f"{API}/documents/{did}", headers=h).status_code == 200
        # file
        files = {"file": ("d.txt", io.BytesIO(b"del"), "text/plain")}
        rf = requests.post(f"{API}/files/upload", headers=h, data={"category": "asset"}, files=files)
        fid = rf.json()["id"]
        assert requests.delete(f"{API}/files/{fid}", headers=h).status_code == 200


class TestRestrictedSubAdmin403:
    """Sub-admin with only ['dashboard'] must get 403 on all 7 gated endpoints,
    and the DB must NOT be mutated (verified by re-fetching as superadmin)."""

    def test_put_quote_403(self, restricted_sub, throwaway_ids, super_token):
        _, tok = restricted_sub
        r = requests.put(
            f"{API}/quotes/{throwaway_ids['quote']}",
            headers=_h(tok),
            json={"status": "HACKED"},
        )
        assert r.status_code == 403, r.text
        # verify not mutated
        g = requests.get(f"{API}/quotes", headers=_h(super_token))
        q = next((x for x in g.json() if x["id"] == throwaway_ids["quote"]), None)
        assert q is not None
        assert q.get("status") != "HACKED"

    def test_delete_quote_403(self, restricted_sub, throwaway_ids, super_token):
        _, tok = restricted_sub
        r = requests.delete(f"{API}/quotes/{throwaway_ids['quote']}", headers=_h(tok))
        assert r.status_code == 403
        # still exists
        g = requests.get(f"{API}/quotes", headers=_h(super_token))
        assert any(x["id"] == throwaway_ids["quote"] for x in g.json())

    def test_delete_service_403(self, restricted_sub, throwaway_ids, super_token):
        _, tok = restricted_sub
        r = requests.delete(f"{API}/services/{throwaway_ids['service']}", headers=_h(tok))
        assert r.status_code == 403
        g = requests.get(f"{API}/services")
        assert any(x["id"] == throwaway_ids["service"] for x in g.json())

    def test_delete_document_403(self, restricted_sub, throwaway_ids, super_token):
        _, tok = restricted_sub
        r = requests.delete(f"{API}/documents/{throwaway_ids['document']}", headers=_h(tok))
        assert r.status_code == 403
        g = requests.get(f"{API}/documents", headers=_h(super_token))
        assert any(x["id"] == throwaway_ids["document"] for x in g.json())

    def test_upload_file_403(self, restricted_sub):
        _, tok = restricted_sub
        files = {"file": ("x.txt", io.BytesIO(b"nope"), "text/plain")}
        r = requests.post(
            f"{API}/files/upload",
            headers=_h(tok),
            data={"category": "asset"},
            files=files,
        )
        assert r.status_code == 403, r.text

    def test_list_files_403(self, restricted_sub):
        _, tok = restricted_sub
        r = requests.get(f"{API}/files", headers=_h(tok))
        assert r.status_code == 403

    def test_delete_file_403(self, restricted_sub, throwaway_ids, super_token):
        _, tok = restricted_sub
        r = requests.delete(f"{API}/files/{throwaway_ids['file']}", headers=_h(tok))
        assert r.status_code == 403
        # file should still not be marked deleted
        g = requests.get(f"{API}/files", headers=_h(super_token))
        assert any(x["id"] == throwaway_ids["file"] for x in g.json())


class TestPermittedSubAdmin:
    """Sub-admin granted crm+services+storage+documents can access the gated endpoints."""

    def test_permitted_put_quote(self, permitted_sub, throwaway_ids):
        _, tok = permitted_sub
        r = requests.put(
            f"{API}/quotes/{throwaway_ids['quote']}",
            headers=_h(tok),
            json={"notes": "ok"},
        )
        assert r.status_code == 200, r.text

    def test_permitted_list_files(self, permitted_sub):
        _, tok = permitted_sub
        r = requests.get(f"{API}/files", headers=_h(tok))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_permitted_upload_and_delete_file(self, permitted_sub):
        _, tok = permitted_sub
        files = {"file": ("p.txt", io.BytesIO(b"perm"), "text/plain")}
        r = requests.post(
            f"{API}/files/upload",
            headers=_h(tok),
            data={"category": "asset"},
            files=files,
        )
        assert r.status_code == 200, r.text
        fid = r.json()["id"]
        r2 = requests.delete(f"{API}/files/{fid}", headers=_h(tok))
        assert r2.status_code == 200

    def test_permitted_delete_service_and_document(self, permitted_sub, super_token):
        _, tok = permitted_sub
        h_super = _h(super_token)
        # create fresh throwaways as super, then delete as permitted sub
        sr = requests.post(f"{API}/services", headers=h_super, json={"title": f"TEST PERM {RUN}"})
        sid = sr.json()["id"]
        r = requests.delete(f"{API}/services/{sid}", headers=_h(tok))
        assert r.status_code == 200, r.text

        dr = requests.post(
            f"{API}/documents",
            headers=h_super,
            json={"doc_type": "quote", "client_name": "PT", "line_items": []},
        )
        did = dr.json()["id"]
        r = requests.delete(f"{API}/documents/{did}", headers=_h(tok))
        assert r.status_code == 200, r.text

    def test_permitted_delete_quote_last(self, permitted_sub, throwaway_ids):
        # delete the throwaway quote last (so preceding restricted tests could see it)
        _, tok = permitted_sub
        r = requests.delete(f"{API}/quotes/{throwaway_ids['quote']}", headers=_h(tok))
        assert r.status_code == 200
