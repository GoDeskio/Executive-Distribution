"""Client Portal feature tests: token gen/revoke + public portal endpoint."""
import os
import io
import uuid
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    return ""

BASE_URL = _load_backend_url()
ADMIN_EMAIL = "admin@executivedistribution.com"
ADMIN_PASSWORD = "Executive2025!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def test_client(auth_headers):
    payload = {
        "name": f"TEST_Portal_{uuid.uuid4().hex[:6]}",
        "company": "TEST Portal Co",
        "email": f"portal_{uuid.uuid4().hex[:6]}@test.com",
        "phone": "+1000000000",
        "country": "US",
        "notes": "",
    }
    r = requests.post(f"{BASE_URL}/api/clients", json=payload, headers=auth_headers, timeout=15)
    assert r.status_code in (200, 201), r.text
    cid = r.json().get("id") or r.json().get("_id")
    yield cid
    requests.delete(f"{BASE_URL}/api/clients/{cid}", headers=auth_headers, timeout=15)


def test_generate_portal_token(auth_headers, test_client):
    r = requests.post(f"{BASE_URL}/api/clients/{test_client}/portal-token", headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text
    token = r.json().get("token")
    assert token and len(token) > 10
    pytest.portal_token = token


def test_public_portal_no_auth(test_client):
    token = pytest.portal_token
    # No Authorization header
    r = requests.get(f"{BASE_URL}/api/portal/{token}", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "client" in data and "company" in data and "documents" in data
    assert data["client"]["name"].startswith("TEST_Portal_")
    assert isinstance(data["documents"], list)
    assert data["company"].get("name")


def test_portal_token_preserved_after_update(auth_headers, test_client):
    token = pytest.portal_token
    # PUT update client - portal_token should be preserved server-side
    payload = {
        "name": "TEST_Portal_Updated",
        "company": "TEST Portal Co Updated",
        "email": f"upd_{uuid.uuid4().hex[:6]}@test.com",
        "phone": "+1", "country": "US", "notes": "",
    }
    up = requests.put(f"{BASE_URL}/api/clients/{test_client}", json=payload, headers=auth_headers, timeout=15)
    assert up.status_code == 200, up.text
    # Ensure portal still accessible
    r = requests.get(f"{BASE_URL}/api/portal/{token}", timeout=15)
    assert r.status_code == 200


def test_document_shows_in_portal(auth_headers, test_client):
    # Create a quote document linked to client
    doc_payload = {
        "doc_type": "quote",
        "client_id": test_client,
        "date": "2026-01-15",
        "port": "Los Angeles",
        "destination": "Tokyo",
        "items": [{"description": "Test item", "quantity": 1, "unit_price": 100, "total": 100}],
        "subtotal": 100,
        "tax": 0,
        "grand_total": 100,
        "notes": "TEST portal doc",
    }
    r = requests.post(f"{BASE_URL}/api/documents", json=doc_payload, headers=auth_headers, timeout=20)
    if r.status_code not in (200, 201):
        pytest.skip(f"Document create failed: {r.status_code} {r.text}")
    doc = r.json()
    doc_id = doc.get("id") or doc.get("_id")
    pytest.doc_id = doc_id
    # Generate PDF
    pdf_r = requests.post(f"{BASE_URL}/api/documents/{doc_id}/generate", headers=auth_headers, timeout=60)
    assert pdf_r.status_code == 200, pdf_r.text
    # Check portal shows it
    token = pytest.portal_token
    portal = requests.get(f"{BASE_URL}/api/portal/{token}", timeout=15).json()
    assert len(portal["documents"]) >= 1
    assert any(d.get("download_url") for d in portal["documents"])
    # download PDF is public
    dl = portal["documents"][0]["download_url"]
    full = f"{BASE_URL}{dl}" if dl.startswith("/") else dl
    d = requests.get(full, timeout=30)
    assert d.status_code == 200
    assert d.content[:4] == b"%PDF" or len(d.content) > 100


def test_portal_isolation_other_client_docs_hidden(auth_headers, test_client):
    # Create another client + doc, ensure not shown in first client's portal
    other = requests.post(f"{BASE_URL}/api/clients", json={
        "name": f"TEST_Other_{uuid.uuid4().hex[:6]}",
        "company": "Other", "email": f"o_{uuid.uuid4().hex[:6]}@t.com",
        "phone": "", "country": "US", "notes": ""
    }, headers=auth_headers, timeout=15)
    other_id = other.json().get("id") or other.json().get("_id")
    try:
        doc_payload = {
            "doc_type": "quote", "client_id": other_id, "date": "2026-01-15",
            "port": "LA", "destination": "X",
            "items": [{"description": "x", "quantity": 1, "unit_price": 10, "total": 10}],
            "subtotal": 10, "tax": 0, "grand_total": 10, "notes": "TEST",
        }
        d = requests.post(f"{BASE_URL}/api/documents", json=doc_payload, headers=auth_headers, timeout=15)
        if d.status_code in (200, 201):
            did = d.json().get("id") or d.json().get("_id")
            requests.post(f"{BASE_URL}/api/documents/{did}/generate", headers=auth_headers, timeout=60)
            token = pytest.portal_token
            portal = requests.get(f"{BASE_URL}/api/portal/{token}", timeout=15).json()
            # None of the docs in first client's portal should belong to other client
            # We assert by counting: reload the first client's portal and verify all docs came from test_client
            # Simplest check: portal should not include documents whose client_id is other_id
            # Since the response doesn't expose client_id, we check that count matches only test_client's docs
            docs_of_first = requests.get(f"{BASE_URL}/api/documents?client_id={test_client}", headers=auth_headers, timeout=15)
            if docs_of_first.status_code == 200:
                first_docs = docs_of_first.json()
                # portal only exposes docs with pdf_file_id; hard to compare exactly, just ensure other doc not visible by number
                other_num = d.json().get("number")
                assert not any(p.get("number") == other_num for p in portal["documents"])
            requests.delete(f"{BASE_URL}/api/documents/{did}", headers=auth_headers, timeout=15)
    finally:
        requests.delete(f"{BASE_URL}/api/clients/{other_id}", headers=auth_headers, timeout=15)


def test_revoke_portal_token(auth_headers, test_client):
    token = pytest.portal_token
    r = requests.delete(f"{BASE_URL}/api/clients/{test_client}/portal-token", headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text
    # Now public access should 404
    g = requests.get(f"{BASE_URL}/api/portal/{token}", timeout=15)
    assert g.status_code == 404
    # Cleanup: delete the doc created
    doc_id = getattr(pytest, "doc_id", None)
    if doc_id:
        requests.delete(f"{BASE_URL}/api/documents/{doc_id}", headers=auth_headers, timeout=15)


def test_invalid_portal_token_returns_404():
    r = requests.get(f"{BASE_URL}/api/portal/nonexistent_token_xyz_12345", timeout=15)
    assert r.status_code == 404
