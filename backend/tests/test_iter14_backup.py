"""Iteration 14: Backup & Restore endpoints (superadmin-only).

Covers:
- RBAC on all /api/backup/* endpoints (superadmin ok, subadmin 403, unauth 401)
- GET /api/backup/config shape
- GET /api/backup/download (with/without files) content-type + zip contents
- POST /api/backup/save + list + download + delete round-trip
- Path traversal protection (404 on bad filenames)
- RESTORE round-trip preserving client + admin login
- Restore with empty/invalid file returns 400
- Regression: audit superadmin-only; sub-admin without crm gets 403 on /api/clients;
  sitemap.xml / robots.txt still valid.
"""
import io
import os
import time
import uuid
import zipfile

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

SUPER_EMAIL = "admin@executivedistribution.com"
SUPER_PASS = "Executive2025!"

TIMEOUT = 60


# ---------- helpers / fixtures ----------

def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password},
                      timeout=TIMEOUT)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text[:200]}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER_EMAIL, SUPER_PASS)


@pytest.fixture(scope="module")
def super_headers(super_token):
    return {"Authorization": f"Bearer {super_token}"}


@pytest.fixture(scope="module")
def sub_admin(super_headers):
    """Create throwaway sub-admin with settings+seo perms; clean up after."""
    email = f"TEST_sub_{uuid.uuid4().hex[:8]}@example.com"
    password = "SubAdmin123!"
    payload = {
        "email": email, "name": "Test Sub Admin",
        "password": password, "role": "subadmin",
        "permissions": ["settings", "seo"],
    }
    r = requests.post(f"{BASE_URL}/api/users", json=payload, headers=super_headers, timeout=TIMEOUT)
    assert r.status_code in (200, 201), f"create sub-admin failed: {r.status_code} {r.text[:200]}"
    user = r.json()
    uid = user.get("id") or user.get("_id")
    token = _login(email, password)
    yield {"email": email, "id": uid, "token": token,
           "headers": {"Authorization": f"Bearer {token}"}}
    # cleanup
    if uid:
        requests.delete(f"{BASE_URL}/api/users/{uid}", headers=super_headers, timeout=TIMEOUT)


# ---------- RBAC ----------

BACKUP_GET_ENDPOINTS = ["/api/backup/config"]
# For endpoints with side effects, we use HEAD-safe testing via unauth first.


class TestBackupRBAC:
    def test_unauth_config(self):
        r = requests.get(f"{BASE_URL}/api/backup/config", timeout=TIMEOUT)
        assert r.status_code == 401

    def test_unauth_download(self):
        r = requests.get(f"{BASE_URL}/api/backup/download?include_files=false", timeout=TIMEOUT)
        assert r.status_code == 401

    def test_unauth_save(self):
        r = requests.post(f"{BASE_URL}/api/backup/save", timeout=TIMEOUT)
        assert r.status_code == 401

    def test_unauth_server_get(self):
        r = requests.get(f"{BASE_URL}/api/backup/server/exd-backup-x.zip", timeout=TIMEOUT)
        assert r.status_code == 401

    def test_unauth_server_delete(self):
        r = requests.delete(f"{BASE_URL}/api/backup/server/exd-backup-x.zip", timeout=TIMEOUT)
        assert r.status_code == 401

    def test_unauth_restore(self):
        r = requests.post(f"{BASE_URL}/api/backup/restore",
                          files={"file": ("x.zip", b"x", "application/zip")},
                          timeout=TIMEOUT)
        assert r.status_code == 401

    def test_subadmin_config_403(self, sub_admin):
        r = requests.get(f"{BASE_URL}/api/backup/config", headers=sub_admin["headers"], timeout=TIMEOUT)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:200]}"

    def test_subadmin_download_403(self, sub_admin):
        r = requests.get(f"{BASE_URL}/api/backup/download?include_files=false",
                         headers=sub_admin["headers"], timeout=TIMEOUT)
        assert r.status_code == 403

    def test_subadmin_save_403(self, sub_admin):
        r = requests.post(f"{BASE_URL}/api/backup/save",
                          headers=sub_admin["headers"], timeout=TIMEOUT)
        assert r.status_code == 403

    def test_subadmin_server_get_403(self, sub_admin):
        r = requests.get(f"{BASE_URL}/api/backup/server/exd-backup-x.zip",
                         headers=sub_admin["headers"], timeout=TIMEOUT)
        assert r.status_code == 403

    def test_subadmin_server_delete_403(self, sub_admin):
        r = requests.delete(f"{BASE_URL}/api/backup/server/exd-backup-x.zip",
                            headers=sub_admin["headers"], timeout=TIMEOUT)
        assert r.status_code == 403

    def test_subadmin_restore_403(self, sub_admin):
        r = requests.post(f"{BASE_URL}/api/backup/restore",
                          headers=sub_admin["headers"],
                          files={"file": ("x.zip", b"x", "application/zip")},
                          timeout=TIMEOUT)
        assert r.status_code == 403


# ---------- config ----------

class TestBackupConfig:
    def test_config_shape(self, super_headers):
        r = requests.get(f"{BASE_URL}/api/backup/config", headers=super_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        for k in ("backup_dir", "effective_dir", "backup_include_files",
                  "backup_auto_before_update", "server_backups"):
            assert k in d, f"missing key {k}"
        assert isinstance(d["server_backups"], list)
        assert isinstance(d["backup_include_files"], bool)
        assert isinstance(d["backup_auto_before_update"], bool)


# ---------- download ----------

class TestBackupDownload:
    def test_download_no_files(self, super_headers):
        r = requests.get(f"{BASE_URL}/api/backup/download?include_files=false",
                         headers=super_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd and "exd-backup-" in cd and ".zip" in cd
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert "data.json" in names
        assert "manifest.json" in names
        # no objects/ entries when include_files=false
        assert not any(n.startswith("objects/") for n in names)

    def test_download_with_files(self, super_headers):
        r = requests.get(f"{BASE_URL}/api/backup/download?include_files=true",
                         headers=super_headers, timeout=180)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        names = zf.namelist()
        assert "data.json" in names
        assert "manifest.json" in names
        # objects/ may be empty if no files uploaded; manifest should reflect that
        import json
        manifest = json.loads(zf.read("manifest.json").decode())
        assert manifest.get("include_files") is True
        assert "object_count" in manifest


# ---------- save + server list + download + delete ----------

class TestServerBackupRoundTrip:
    def test_save_list_download_delete(self, super_headers):
        # save
        r = requests.post(f"{BASE_URL}/api/backup/save", headers=super_headers, timeout=180)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("ok") is True
        fname = d.get("filename")
        assert fname and fname.startswith("exd-backup-") and fname.endswith(".zip")
        assert d.get("path")
        assert isinstance(d.get("size"), int) and d["size"] > 0

        # list via config
        r2 = requests.get(f"{BASE_URL}/api/backup/config", headers=super_headers, timeout=TIMEOUT)
        assert r2.status_code == 200
        assert any(b["filename"] == fname for b in r2.json()["server_backups"])

        # download
        r3 = requests.get(f"{BASE_URL}/api/backup/server/{fname}",
                          headers=super_headers, timeout=180)
        assert r3.status_code == 200
        assert r3.headers.get("content-type", "").startswith("application/zip")
        # must be a valid zip
        zipfile.ZipFile(io.BytesIO(r3.content))

        # delete
        r4 = requests.delete(f"{BASE_URL}/api/backup/server/{fname}",
                             headers=super_headers, timeout=TIMEOUT)
        assert r4.status_code == 200
        assert r4.json().get("ok") is True

        # confirm removed
        r5 = requests.get(f"{BASE_URL}/api/backup/config", headers=super_headers, timeout=TIMEOUT)
        assert not any(b["filename"] == fname for b in r5.json()["server_backups"])


# ---------- path traversal protection ----------

class TestPathTraversal:
    def test_traversal_encoded(self, super_headers):
        # URL-encoded traversal — must NOT serve arbitrary files
        r = requests.get(f"{BASE_URL}/api/backup/server/..%2f..%2fetc%2fpasswd",
                         headers=super_headers, timeout=TIMEOUT)
        assert r.status_code == 404, f"expected 404, got {r.status_code}"

    def test_bad_prefix(self, super_headers):
        r = requests.get(f"{BASE_URL}/api/backup/server/notabackup.zip",
                         headers=super_headers, timeout=TIMEOUT)
        assert r.status_code == 404

    def test_delete_bad_prefix(self, super_headers):
        r = requests.delete(f"{BASE_URL}/api/backup/server/notabackup.zip",
                            headers=super_headers, timeout=TIMEOUT)
        # returns 200 with ok:false (documented behavior)
        assert r.status_code == 200
        assert r.json().get("ok") is False


# ---------- RESTORE round-trip ----------

class TestRestoreRoundTrip:
    def test_restore_preserves_client_and_login(self, super_headers):
        # a) create distinctive client
        cname = f"BACKUP-RT-{uuid.uuid4().hex[:8]}"
        r = requests.post(f"{BASE_URL}/api/clients",
                          json={"name": cname, "email": f"{cname}@example.com"},
                          headers=super_headers, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text[:300]
        client = r.json()
        cid = client.get("id") or client.get("_id")
        assert cid, f"no id in create response: {client}"

        # get pre-count
        rlist = requests.get(f"{BASE_URL}/api/clients", headers=super_headers, timeout=TIMEOUT)
        assert rlist.status_code == 200
        pre_items = rlist.json()
        pre_items = pre_items if isinstance(pre_items, list) else pre_items.get("items", [])
        pre_count = len(pre_items)
        assert any((c.get("id") or c.get("_id")) == cid for c in pre_items), "created client missing"

        # b) download full backup
        rb = requests.get(f"{BASE_URL}/api/backup/download?include_files=true",
                          headers=super_headers, timeout=180)
        assert rb.status_code == 200
        zip_bytes = rb.content
        # sanity — must be a real zip
        zipfile.ZipFile(io.BytesIO(zip_bytes))

        # c) delete the client
        rd = requests.delete(f"{BASE_URL}/api/clients/{cid}", headers=super_headers, timeout=TIMEOUT)
        assert rd.status_code in (200, 204)

        # verify deleted
        rlist2 = requests.get(f"{BASE_URL}/api/clients", headers=super_headers, timeout=TIMEOUT)
        items2 = rlist2.json()
        items2 = items2 if isinstance(items2, list) else items2.get("items", [])
        assert not any((c.get("id") or c.get("_id")) == cid for c in items2), \
            "client still present after delete"

        # d) restore
        rr = requests.post(
            f"{BASE_URL}/api/backup/restore",
            headers=super_headers,
            files={"file": (f"exd-backup-restore.zip", zip_bytes, "application/zip")},
            timeout=300,
        )
        assert rr.status_code == 200, f"restore failed: {rr.status_code} {rr.text[:400]}"
        body = rr.json()
        assert body.get("ok") is True
        assert "restored" in body

        # e) client should be back
        rlist3 = requests.get(f"{BASE_URL}/api/clients", headers=super_headers, timeout=TIMEOUT)
        assert rlist3.status_code == 200
        items3 = rlist3.json()
        items3 = items3 if isinstance(items3, list) else items3.get("items", [])
        assert len(items3) == pre_count, f"count differs: pre={pre_count} post={len(items3)}"
        assert any((c.get("id") or c.get("_id")) == cid for c in items3), \
            "restored client missing"

        # login still works (password_hash preserved through restore)
        tok = _login(SUPER_EMAIL, SUPER_PASS)
        assert tok

        # cleanup: delete the throwaway client
        requests.delete(f"{BASE_URL}/api/clients/{cid}", headers=super_headers, timeout=TIMEOUT)


# ---------- restore error handling ----------

class TestRestoreErrors:
    def test_restore_empty(self, super_headers):
        r = requests.post(f"{BASE_URL}/api/backup/restore",
                          headers=super_headers,
                          files={"file": ("empty.zip", b"", "application/zip")},
                          timeout=TIMEOUT)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:200]}"

    def test_restore_invalid_zip(self, super_headers):
        r = requests.post(f"{BASE_URL}/api/backup/restore",
                          headers=super_headers,
                          files={"file": ("garbage.zip", b"not a zip at all", "application/zip")},
                          timeout=TIMEOUT)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:200]}"


# ---------- regressions ----------

class TestRegressions:
    def test_super_login(self):
        assert _login(SUPER_EMAIL, SUPER_PASS)

    def test_audit_superadmin_only(self, sub_admin):
        r = requests.get(f"{BASE_URL}/api/audit", headers=sub_admin["headers"], timeout=TIMEOUT)
        assert r.status_code == 403

    def test_audit_super_ok(self, super_headers):
        r = requests.get(f"{BASE_URL}/api/audit", headers=super_headers, timeout=TIMEOUT)
        assert r.status_code == 200

    def test_subadmin_without_crm_gets_403_on_clients(self, sub_admin):
        # sub_admin has settings+seo but NOT crm
        r = requests.get(f"{BASE_URL}/api/clients", headers=sub_admin["headers"], timeout=TIMEOUT)
        assert r.status_code == 403

    def test_sitemap(self):
        r = requests.get(f"{BASE_URL}/api/sitemap.xml", timeout=TIMEOUT)
        # sitemap may live at /sitemap.xml (no /api prefix) too — try both
        if r.status_code == 404:
            r = requests.get(f"{BASE_URL}/sitemap.xml", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "<urlset" in r.text or "<sitemapindex" in r.text

    def test_robots(self):
        r = requests.get(f"{BASE_URL}/api/robots.txt", timeout=TIMEOUT)
        if r.status_code == 404:
            r = requests.get(f"{BASE_URL}/robots.txt", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "User-agent" in r.text or "user-agent" in r.text.lower()
