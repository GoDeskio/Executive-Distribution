"""Iter8: Slack + Stytch integration settings sanitization, and portal approve with alerts."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@executivedistribution.com"
ADMIN_PASS = "Executive2025!"

SECRET_KEYS = ["slack_webhook_url", "stytch_secret", "ai_own_key", "email_api_key"]


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"] if "access_token" in r.json() else r.json().get("token")


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def original_settings(auth):
    r = requests.get(f"{API}/settings", timeout=15)
    assert r.status_code == 200
    return r.json()


def _assert_no_secrets(payload):
    for k in SECRET_KEYS:
        assert k not in payload, f"Secret leaked in response: {k}"


def test_get_settings_sanitized(original_settings):
    _assert_no_secrets(original_settings)
    # boolean has_* flags must exist
    assert "has_slack_webhook" in original_settings
    assert "has_stytch_secret" in original_settings


def test_put_settings_sanitized_and_persist(auth):
    payload = {
        "slack_webhook_url": "https://hooks.slack.com/services/TEST/xxx/TEST_IT8",
        "alert_on_approval": True,
        "social_login_enabled": True,
        "stytch_project_id": "project-test-TEST_IT8",
        "stytch_secret": "secret-TEST_IT8-should-not-leak",
    }
    r = requests.put(f"{API}/settings", json=payload, headers=auth, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    _assert_no_secrets(body)
    assert body.get("alert_on_approval") is True
    assert body.get("social_login_enabled") is True
    assert body.get("stytch_project_id") == "project-test-TEST_IT8"
    assert body.get("has_slack_webhook") is True
    assert body.get("has_stytch_secret") is True

    # Re-GET
    r2 = requests.get(f"{API}/settings", timeout=15)
    b2 = r2.json()
    _assert_no_secrets(b2)
    assert b2.get("alert_on_approval") is True
    assert b2.get("social_login_enabled") is True
    assert b2.get("stytch_project_id") == "project-test-TEST_IT8"
    assert b2.get("has_slack_webhook") is True
    assert b2.get("has_stytch_secret") is True


def test_put_settings_without_secret_keeps_existing(auth):
    """Sending payload without stytch_secret/slack_webhook_url should NOT clear them (frontend sends only when typed)."""
    r = requests.put(f"{API}/settings", json={"alert_on_approval": True}, headers=auth, timeout=15)
    assert r.status_code == 200
    b = r.json()
    assert b.get("has_slack_webhook") is True
    assert b.get("has_stytch_secret") is True


@pytest.fixture(scope="module")
def client_and_quote(auth):
    # Create a TEST_ client
    cr = requests.post(f"{API}/clients", json={
        "name": "TEST_IT8 Client", "company": "TEST_IT8 Co",
        "email": "test_it8@example.com", "phone": "5555555555",
    }, headers=auth, timeout=15)
    assert cr.status_code == 200, cr.text
    client = cr.json()
    cid = client["id"]

    # Create a quote/document
    dr = requests.post(f"{API}/documents", json={
        "client_id": cid, "doc_type": "quote",
        "items": [{"description": "TEST widget", "quantity": 2, "unit_price": 100.0}],
        "port": "Miami", "destination": "Nassau",
    }, headers=auth, timeout=20)
    assert dr.status_code == 200, dr.text
    doc = dr.json()
    doc_id = doc["id"]

    # Generate PDF
    pr = requests.post(f"{API}/documents/{doc_id}/generate", headers=auth, timeout=45)
    assert pr.status_code == 200, pr.text

    # Portal token
    tr = requests.post(f"{API}/clients/{cid}/portal-token", json={}, headers=auth, timeout=15)
    assert tr.status_code == 200, tr.text
    portal_token = tr.json()["token"]

    yield {"client_id": cid, "doc_id": doc_id, "portal_token": portal_token}

    # Cleanup
    try:
        requests.delete(f"{API}/documents/{doc_id}", headers=auth, timeout=15)
    except Exception:
        pass
    try:
        requests.delete(f"{API}/clients/{cid}", headers=auth, timeout=15)
    except Exception:
        pass


def test_portal_approve_with_fake_slack_webhook(auth, client_and_quote):
    # Ensure alerts on + fake webhook set (from earlier tests)
    portal_token = client_and_quote["portal_token"]
    doc_id = client_and_quote["doc_id"]

    # Unauthenticated portal fetch
    pr = requests.get(f"{API}/portal/{portal_token}", timeout=15)
    assert pr.status_code == 200, pr.text
    assert any(d["id"] == doc_id for d in pr.json().get("documents", []))

    t0 = time.time()
    ar = requests.post(f"{API}/portal/{portal_token}/approve", json={"document_id": doc_id}, timeout=20)
    elapsed = time.time() - t0
    assert ar.status_code == 200, ar.text
    assert ar.json().get("status") == "approved"
    # Should not hang > 12s despite fake webhook (timeout is 8)
    assert elapsed < 15, f"Approve took too long: {elapsed}s"

    # Notification should be created
    nr = requests.get(f"{API}/notifications", headers=auth, timeout=15)
    assert nr.status_code == 200
    notes = nr.json()
    assert any(n.get("document_id") == doc_id and n.get("type") == "quote_approved" for n in notes)


def test_portal_approve_no_slack_when_disabled(auth):
    """Turn alerts off + also clear webhook via empty string; approve should still work."""
    # Disable alert + set webhook to empty explicitly
    r = requests.put(f"{API}/settings", json={
        "alert_on_approval": False,
        "slack_webhook_url": "",
        "stytch_secret": "",
        "social_login_enabled": False,
        "stytch_project_id": "",
    }, headers=auth, timeout=15)
    assert r.status_code == 200
    b = r.json()
    _assert_no_secrets(b)
    assert b.get("has_slack_webhook") is False
    assert b.get("has_stytch_secret") is False
    assert b.get("alert_on_approval") is False

    # Create fresh client+quote for a clean approve
    cr = requests.post(f"{API}/clients", json={
        "name": "TEST_IT8_B Client", "company": "TEST_IT8_B",
        "email": "test_it8b@example.com", "phone": "5555555556",
    }, headers=auth, timeout=15)
    cid = cr.json()["id"]
    dr = requests.post(f"{API}/documents", json={
        "client_id": cid, "doc_type": "quote",
        "items": [{"description": "TEST b", "quantity": 1, "unit_price": 50.0}],
    }, headers=auth, timeout=20)
    doc_id = dr.json()["id"]
    requests.post(f"{API}/documents/{doc_id}/generate", headers=auth, timeout=45)
    tr = requests.post(f"{API}/clients/{cid}/portal-token", json={}, headers=auth, timeout=15)
    ptoken = tr.json()["token"]

    ar = requests.post(f"{API}/portal/{ptoken}/approve", json={"document_id": doc_id}, timeout=20)
    assert ar.status_code == 200, ar.text
    assert ar.json().get("status") == "approved"

    # cleanup
    requests.delete(f"{API}/documents/{doc_id}", headers=auth, timeout=15)
    requests.delete(f"{API}/clients/{cid}", headers=auth, timeout=15)
