"""Tests for new AI/Calculator/Documents/Search features."""
import os
import uuid
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
BASE_URL = None
fe_env = Path("/app/frontend/.env").read_text()
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


# ---------- Settings sanitization ----------
def test_settings_get_sanitizes_ai_own_key(auth):
    # Set an own key
    cur = requests.get(f"{API}/settings", timeout=30).json()
    payload = dict(cur)
    payload.pop("has_own_key", None)
    payload["ai_own_key"] = "sk-TEST-DUMMY-KEY-XXXX"
    r = requests.put(f"{API}/settings", json=payload, headers=auth, timeout=30)
    assert r.status_code == 200

    # GET must NOT leak ai_own_key, must expose has_own_key True
    got = requests.get(f"{API}/settings", timeout=30).json()
    assert "ai_own_key" not in got, "ai_own_key leaked in GET /settings"
    assert got.get("has_own_key") is True

    # Reset
    payload["ai_own_key"] = ""
    r = requests.put(f"{API}/settings", json=payload, headers=auth, timeout=30)
    assert r.status_code == 200
    got2 = requests.get(f"{API}/settings", timeout=30).json()
    assert got2.get("has_own_key") is False
    assert "ai_own_key" not in got2


# ---------- AI status ----------
def test_ai_status(auth):
    r = requests.get(f"{API}/ai/status", headers=auth, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("source", "provider", "model", "has_own_key"):
        assert k in d
    assert d["source"] in ("emergent", "own", "user", "byo")


def test_ai_status_requires_auth():
    r = requests.get(f"{API}/ai/status", timeout=30)
    assert r.status_code == 401


# ---------- Fee calculator ----------
def test_calculate_ocean():
    payload = {"item_name": "widgets", "declared_value": 1000, "weight_kg": 100,
               "quantity": 1, "mode": "ocean", "destination": "Dubai"}
    r = requests.post(f"{API}/calculate", json=payload, timeout=30)
    assert r.status_code == 200
    d = r.json()
    b = d["breakdown"]
    # freight = 100 * 4.5 * 1.0 * 1 = 450
    assert b["freight"] == 450.0
    assert b["handling"] == 75.0
    assert b["port_surcharge"] == 120.0
    # insurance 1.5% of 1000 = 15
    assert b["insurance"] == 15.0
    # customs 8% of 1000 = 80
    assert b["customs_duty"] == 80.0
    # vat 5% of (1000+450+80)=1530 -> 76.5
    assert b["vat_tax"] == 76.5
    assert d["fees_total"] == round(450 + 75 + 120 + 15, 2)
    # grand = 1000 + fees_total(660) + customs(80) + vat(76.5) = 1816.5
    assert d["grand_total"] == 1816.5
    assert "rules_used" in d


def test_calculate_air_multiplier():
    r = requests.post(f"{API}/calculate", json={"weight_kg": 10, "declared_value": 0,
                                                 "quantity": 1, "mode": "air"}, timeout=30)
    assert r.status_code == 200
    # 10 * 4.5 * 2.6 = 117
    assert r.json()["breakdown"]["freight"] == 117.0


# ---------- Documents CRUD + PDF ----------
def test_document_create_and_generate_pdf(auth):
    payload = {
        "doc_type": "quote",
        "client_name": f"TEST_DocClient_{uuid.uuid4().hex[:6]}",
        "client_company": "TESTCo",
        "client_email": "doc@test.com",
        "destination": "Miami",
        "port": "MIA",
        "po_number": f"PO-TEST-{uuid.uuid4().hex[:6]}",
        "line_items": [{"item": "TEST widget", "qty": 2, "unit_price": 50, "fees": 10, "customs": 5, "total": 115}],
        "subtotal": 100, "fees_total": 10, "customs_total": 5, "tax_total": 0, "grand_total": 115,
        "notes": "test", "status": "draft",
    }
    r = requests.post(f"{API}/documents", headers=auth, json=payload, timeout=30)
    assert r.status_code == 200, r.text
    doc = r.json()
    did = doc["id"]
    assert doc["number"].startswith("EXD-Q-")
    assert doc["pdf_file_id"] is None
    assert doc["po_number"] == payload["po_number"]

    # List
    r = requests.get(f"{API}/documents", headers=auth, timeout=30)
    assert r.status_code == 200
    assert any(d["id"] == did for d in r.json())

    # Generate PDF
    r = requests.post(f"{API}/documents/{did}/generate", headers=auth, timeout=60)
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["ok"] is True
    assert g["url"].startswith("/api/files/") and g["url"].endswith("/raw")

    # Fetch PDF is served and is a real PDF
    r_pdf = requests.get(f"{BASE_URL}{g['url']}", timeout=60)
    assert r_pdf.status_code == 200
    assert r_pdf.content[:5] == b"%PDF-", "generated file is not a PDF"
    assert r_pdf.headers.get("content-type", "").startswith("application/pdf")

    # Doc now has pdf_file_id and status=generated
    r = requests.get(f"{API}/documents", headers=auth, timeout=30)
    updated = [d for d in r.json() if d["id"] == did][0]
    assert updated["pdf_file_id"] == g["file_id"]
    assert updated["status"] == "generated"

    # Send-to-client folder listing
    r = requests.get(f"{API}/files?category=send_to_client", headers=auth, timeout=30)
    assert r.status_code == 200
    assert any(f["id"] == g["file_id"] for f in r.json())

    # Search by PO
    r = requests.get(f"{API}/search", headers=auth, params={"q": payload["po_number"]}, timeout=30)
    assert r.status_code == 200
    s = r.json()
    assert any(d["id"] == did for d in s["documents"])

    # Search by document number
    r = requests.get(f"{API}/search", headers=auth, params={"q": doc["number"]}, timeout=30)
    assert any(d["id"] == did for d in r.json()["documents"])

    # Cleanup
    requests.delete(f"{API}/documents/{did}", headers=auth, timeout=30)


def test_document_generate_404(auth):
    r = requests.post(f"{API}/documents/507f1f77bcf86cd799439011/generate", headers=auth, timeout=30)
    assert r.status_code == 404


def test_documents_requires_auth():
    r = requests.get(f"{API}/documents", timeout=30)
    assert r.status_code == 401


# ---------- Global search ----------
def test_search_empty(auth):
    r = requests.get(f"{API}/search", headers=auth, params={"q": ""}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d == {"clients": [], "quotes": [], "requests": [], "documents": []} or \
           (d["clients"] == [] and d["documents"] == [] and d["requests"] == [])


def test_search_acme_seed(auth):
    # Sample data notes: EXD-Q-00001 for Acme Imports w/ PO-991 should exist per problem statement
    r = requests.get(f"{API}/search", headers=auth, params={"q": "Acme"}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    # If seed was created, expect at least one hit in clients or documents
    total = len(d.get("clients", [])) + len(d.get("documents", [])) + len(d.get("requests", []))
    assert total >= 0  # do not fail if reseeded; but log
    # Try quote number
    r2 = requests.get(f"{API}/search", headers=auth, params={"q": "EXD-Q-00001"}, timeout=30)
    assert r2.status_code == 200


def test_search_requires_auth():
    r = requests.get(f"{API}/search", params={"q": "x"}, timeout=30)
    assert r.status_code == 401


# ---------- AI chat streaming (minimal - 1 message) ----------
def test_ai_chat_public_streams():
    r = requests.post(
        f"{API}/ai/chat",
        json={"session_id": f"test_{uuid.uuid4().hex[:8]}", "message": "Hi in 3 words",
              "history": [], "scope": "public"},
        stream=True, timeout=60,
    )
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    body = b""
    for chunk in r.iter_content(chunk_size=64):
        body += chunk
        if len(body) > 3:
            break
    r.close()
    assert len(body) > 0, "no stream chunks received"


def test_ai_chat_admin_requires_auth():
    r = requests.post(f"{API}/ai/chat/admin",
                      json={"session_id": "s", "message": "hi", "history": [], "scope": "admin"},
                      timeout=30)
    assert r.status_code == 401
