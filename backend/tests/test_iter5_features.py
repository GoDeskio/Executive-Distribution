"""Iteration 5: HS code persistence, AI refine, direct PDF download, Integrations settings."""
import os
import uuid
import pytest
import requests
from pathlib import Path

fe_env = Path("/app/frontend/.env").read_text()
BASE_URL = None
for line in fe_env.splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@executivedistribution.com"
ADMIN_PASSWORD = "Executive2025!"


@pytest.fixture(scope="module")
def auth():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ---------- HS Code persistence ----------
def test_hs_code_persists_on_document(auth):
    payload = {
        "doc_type": "quote",
        "client_name": f"TEST_HS_{uuid.uuid4().hex[:6]}",
        "line_items": [
            {"item": "TEST cigars", "hs_code": "240210", "qty": 10, "unit_price": 5,
             "fees": 0, "customs": 0, "total": 50}
        ],
        "subtotal": 50, "fees_total": 0, "customs_total": 0, "tax_total": 0, "grand_total": 50,
        "status": "draft",
    }
    r = requests.post(f"{API}/documents", headers=auth, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    doc = r.json()
    did = doc["id"]
    try:
        # GET list and find it
        r2 = requests.get(f"{API}/documents", headers=auth, timeout=30)
        assert r2.status_code == 200
        found = [d for d in r2.json() if d["id"] == did][0]
        assert found["line_items"][0]["hs_code"] == "240210", f"hs_code not persisted: {found['line_items'][0]}"
        assert found["line_items"][0]["item"] == "TEST cigars"
    finally:
        requests.delete(f"{API}/documents/{did}", headers=auth, timeout=30)


# ---------- AI Draft returns HS codes (single call - minimal) ----------
def test_ai_draft_returns_hs_code_field(auth):
    r = requests.post(
        f"{API}/documents/ai-draft",
        headers=auth,
        json={"description": "20 pallets of green coffee beans from Colombia to Miami", "doc_type": "quote"},
        timeout=90,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "line_items" in data
    assert len(data["line_items"]) >= 1
    # every line item should have hs_code field present (may be empty for edge cases)
    for li in data["line_items"]:
        assert "hs_code" in li, f"missing hs_code in line item: {li}"
    # At least one line should have a non-empty hs_code (AI should suggest for coffee)
    non_empty = [li for li in data["line_items"] if str(li.get("hs_code", "")).strip()]
    assert len(non_empty) >= 1, f"No hs_code populated by AI. items: {data['line_items']}"


# ---------- Direct PDF download via /api/files/{id}/raw ----------
def test_pdf_direct_download_after_generate(auth):
    payload = {
        "doc_type": "quote",
        "client_name": f"TEST_PDF_{uuid.uuid4().hex[:6]}",
        "line_items": [{"item": "TEST tobacco", "hs_code": "240210", "qty": 1, "unit_price": 100,
                        "fees": 5, "customs": 8, "total": 113}],
        "subtotal": 100, "fees_total": 5, "customs_total": 8, "tax_total": 0, "grand_total": 113,
        "status": "draft",
    }
    r = requests.post(f"{API}/documents", headers=auth, json=payload, timeout=30)
    assert r.status_code == 200
    did = r.json()["id"]
    try:
        g = requests.post(f"{API}/documents/{did}/generate", headers=auth, timeout=60)
        assert g.status_code == 200, g.text
        gj = g.json()
        assert gj["url"].endswith("/raw")
        pdf_file_id = gj["file_id"]

        # Direct download via raw endpoint (public - simulates row-download button)
        raw = requests.get(f"{API}/files/{pdf_file_id}/raw", timeout=60)
        assert raw.status_code == 200
        assert raw.content[:5] == b"%PDF-"
        assert raw.headers.get("content-type", "").startswith("application/pdf")

        # Confirm doc row includes pdf_file_id (needed for row-download-{id})
        docs = requests.get(f"{API}/documents", headers=auth, timeout=30).json()
        updated = [d for d in docs if d["id"] == did][0]
        assert updated["pdf_file_id"] == pdf_file_id
    finally:
        requests.delete(f"{API}/documents/{did}", headers=auth, timeout=30)


# ---------- Integrations settings: save + sanitize ----------
def test_integrations_email_settings_persist_and_sanitize(auth):
    # Capture current settings (public sanitized view)
    initial = requests.get(f"{API}/settings", timeout=30).json()
    # Save integrations
    payload = dict(initial)
    payload.pop("has_own_key", None)
    payload.pop("has_email_key", None)
    payload["email_provider"] = "resend"
    payload["email_from"] = "quotes@testexecdist.com"
    payload["email_api_key"] = "re_TEST_DUMMY_KEY_12345"

    r = requests.put(f"{API}/settings", json=payload, headers=auth, timeout=30)
    assert r.status_code == 200, r.text

    # Reload via public GET
    got = requests.get(f"{API}/settings", timeout=30).json()
    assert got.get("email_provider") == "resend"
    assert got.get("email_from") == "quotes@testexecdist.com"
    assert got.get("has_email_key") is True
    # CRITICAL: raw secrets must never be exposed
    assert "email_api_key" not in got, f"email_api_key leaked: {got}"
    assert "ai_own_key" not in got, f"ai_own_key leaked: {got}"

    # Save again WITHOUT sending the api key (simulating "key on file" reload+save)
    payload2 = dict(got)
    payload2.pop("has_own_key", None)
    payload2.pop("has_email_key", None)
    # Should NOT include email_api_key => existing key preserved
    r2 = requests.put(f"{API}/settings", json=payload2, headers=auth, timeout=30)
    assert r2.status_code == 200
    got2 = requests.get(f"{API}/settings", timeout=30).json()
    assert got2.get("has_email_key") is True, "existing email key was wiped when not resent"
    assert got2.get("email_provider") == "resend"

    # Cleanup - clear the key
    payload3 = dict(got2)
    payload3.pop("has_own_key", None)
    payload3.pop("has_email_key", None)
    payload3["email_api_key"] = ""
    payload3["email_provider"] = initial.get("email_provider", "none")
    payload3["email_from"] = initial.get("email_from", "")
    r3 = requests.put(f"{API}/settings", json=payload3, headers=auth, timeout=30)
    assert r3.status_code == 200
    got3 = requests.get(f"{API}/settings", timeout=30).json()
    assert got3.get("has_email_key") is False


def test_settings_put_requires_auth():
    r = requests.put(f"{API}/settings", json={"email_provider": "resend"}, timeout=30)
    assert r.status_code == 401
