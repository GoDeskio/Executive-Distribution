"""Backend API tests for Executive Distribution."""
import os
import io
import uuid
import time
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # fallback: read from frontend .env
    fe_env = Path("/app/frontend/.env").read_text()
    for line in fe_env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@executivedistribution.com"
ADMIN_PASSWORD = "Executive2025!"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and "user" in data
    return data["token"]


@pytest.fixture(scope="session")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Auth ----------
def test_login_invalid():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=30)
    assert r.status_code == 401


def test_me(auth):
    r = requests.get(f"{API}/auth/me", headers=auth, timeout=30)
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL


def test_me_unauthorized():
    r = requests.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 401


# ---------- Services ----------
def test_list_services_public():
    r = requests.get(f"{API}/services", timeout=30)
    assert r.status_code == 200
    services = r.json()
    assert isinstance(services, list)
    assert len(services) >= 1
    assert "slug" in services[0]


def test_get_service_by_slug():
    r = requests.get(f"{API}/services", timeout=30)
    slug = r.json()[0]["slug"]
    r2 = requests.get(f"{API}/services/{slug}", timeout=30)
    assert r2.status_code == 200
    assert r2.json()["slug"] == slug


def test_service_crud(auth):
    payload = {
        "title": f"TEST_Service_{uuid.uuid4().hex[:6]}",
        "short_description": "sd",
        "full_description": "fd",
        "icon": "package",
        "published": True,
        "features": ["f1", "f2"],
        "meta_title": "mt",
        "meta_description": "md",
        "keywords": "kw",
    }
    r = requests.post(f"{API}/services", json=payload, headers=auth, timeout=30)
    assert r.status_code == 200, r.text
    created = r.json()
    sid = created["id"]
    slug = created["slug"]
    assert created["title"] == payload["title"]

    # public GET
    r = requests.get(f"{API}/services/{slug}", timeout=30)
    assert r.status_code == 200

    # UPDATE
    payload["title"] = payload["title"] + "_UPD"
    r = requests.put(f"{API}/services/{sid}", json=payload, headers=auth, timeout=30)
    assert r.status_code == 200
    assert r.json()["title"].endswith("_UPD")

    # DELETE
    r = requests.delete(f"{API}/services/{sid}", headers=auth, timeout=30)
    assert r.status_code == 200

    r = requests.get(f"{API}/services/{slug}", timeout=30)
    assert r.status_code == 404


# ---------- Settings ----------
def test_settings_get_and_update(auth):
    r = requests.get(f"{API}/settings", timeout=30)
    assert r.status_code == 200
    original = r.json()
    orig_title = original.get("seo_title", "")

    new = dict(original)
    new["seo_title"] = "TEST_SEO_" + uuid.uuid4().hex[:6]
    r = requests.put(f"{API}/settings", json=new, headers=auth, timeout=30)
    assert r.status_code == 200
    assert r.json()["seo_title"] == new["seo_title"]

    # restore
    new["seo_title"] = orig_title
    requests.put(f"{API}/settings", json=new, headers=auth, timeout=30)


def test_settings_unauth():
    r = requests.put(f"{API}/settings", json={"seo_title": "x"}, timeout=30)
    assert r.status_code == 401


# ---------- Clients CRUD ----------
def test_clients_crud(auth):
    payload = {"name": f"TEST_Client_{uuid.uuid4().hex[:6]}", "company": "Acme",
               "email": "c@e.com", "phone": "123", "status": "lead", "value": 100, "tags": ["vip"], "notes": "n"}
    r = requests.post(f"{API}/clients", json=payload, headers=auth, timeout=30)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    assert r.json()["name"] == payload["name"]

    r = requests.get(f"{API}/clients", headers=auth, timeout=30)
    assert r.status_code == 200
    assert any(c["id"] == cid for c in r.json())

    payload["name"] = payload["name"] + "_UPD"
    r = requests.put(f"{API}/clients/{cid}", json=payload, headers=auth, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"].endswith("_UPD")

    r = requests.delete(f"{API}/clients/{cid}", headers=auth, timeout=30)
    assert r.status_code == 200


# ---------- Tracking & analytics ----------
def test_track_and_analytics(auth):
    sid = f"TEST_sess_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/track", json={"session_id": sid, "path": "/", "event_type": "pageview",
                                            "viewport_w": 1920, "viewport_h": 1080}, timeout=30)
    assert r.status_code == 200
    r = requests.post(f"{API}/track", json={"session_id": sid, "path": "/", "event_type": "click",
                                            "x": 0.5, "y": 0.5}, timeout=30)
    assert r.status_code == 200

    r = requests.get(f"{API}/analytics/overview", headers=auth, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "total_visitors" in d and "total_views" in d

    r = requests.get(f"{API}/analytics/timeseries?days=14", headers=auth, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = requests.get(f"{API}/analytics/pages", headers=auth, timeout=30)
    assert r.status_code == 200

    r = requests.get(f"{API}/analytics/heatmap?path=/", headers=auth, timeout=30)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    r = requests.get(f"{API}/analytics/visitors", headers=auth, timeout=30)
    assert r.status_code == 200
    assert any(v.get("session_id") == sid for v in r.json())


# ---------- Files upload/list/serve/delete ----------
def test_files_flow(auth):
    # tiny PNG
    png = bytes.fromhex("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
    files = {"file": ("test.png", io.BytesIO(png), "image/png")}
    data = {"category": "asset"}
    r = requests.post(f"{API}/files/upload", headers=auth, files=files, data=data, timeout=60)
    assert r.status_code == 200, r.text
    fid = r.json()["id"]
    url = r.json()["url"]
    assert url.startswith("/api/files/")

    # list
    r = requests.get(f"{API}/files?category=asset", headers=auth, timeout=30)
    assert r.status_code == 200
    assert any(f["id"] == fid for f in r.json())

    # raw serve (public)
    r = requests.get(f"{BASE_URL}{url}", timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("image/")

    # delete
    r = requests.delete(f"{API}/files/{fid}", headers=auth, timeout=30)
    assert r.status_code == 200


# ---------- Profile ----------
def test_profile_update_name(auth):
    r = requests.put(f"{API}/auth/profile", headers=auth, json={"name": "Executive Admin"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["name"] == "Executive Admin"


def test_profile_wrong_current_password(auth):
    r = requests.put(f"{API}/auth/profile", headers=auth,
                     json={"current_password": "wrong", "new_password": "SomethingNew1!"}, timeout=30)
    assert r.status_code == 400


# ---------- Quotes (public create + admin CRUD) ----------
PNG_BYTES = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000A"
    "49444154789C6300010000000500010D0A2DB40000000049454E44AE426082"
)


def test_quote_create_public_no_images():
    data = {
        "name": f"TEST_Buyer_{uuid.uuid4().hex[:6]}",
        "email": "buyer@example.com",
        "company": "TEST Co",
        "phone": "+123",
        "destination": "Dubai",
        "description": "Need 5000 units of widgets",
    }
    r = requests.post(f"{API}/quotes", data=data, timeout=30)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("ok") is True
    assert "id" in j


def test_quote_create_requires_name_email():
    # Missing name -> 422 (FastAPI Form validation)
    r = requests.post(f"{API}/quotes", data={"email": "x@x.com"}, timeout=30)
    assert r.status_code == 422
    r = requests.post(f"{API}/quotes", data={"name": "n"}, timeout=30)
    assert r.status_code == 422


def test_quote_create_with_images_and_admin_flow(auth):
    name = f"TEST_QImg_{uuid.uuid4().hex[:6]}"
    data = {"name": name, "email": "img@example.com", "company": "C", "phone": "1",
            "destination": "LA", "description": "with images"}
    files = [
        ("images", ("a.png", io.BytesIO(PNG_BYTES), "image/png")),
        ("images", ("b.png", io.BytesIO(PNG_BYTES), "image/png")),
    ]
    r = requests.post(f"{API}/quotes", data=data, files=files, timeout=60)
    assert r.status_code == 200, r.text
    qid = r.json()["id"]

    # List (auth) and find our quote
    r = requests.get(f"{API}/quotes", headers=auth, timeout=30)
    assert r.status_code == 200
    quotes = r.json()
    mine = [q for q in quotes if q.get("id") == qid]
    assert mine, "created quote missing from list"
    q = mine[0]
    assert q["name"] == name
    assert q["status"] == "new"
    assert isinstance(q.get("images"), list) and len(q["images"]) == 2
    # image url loads
    img_url = q["images"][0]
    assert img_url.startswith("/api/files/") and img_url.endswith("/raw")
    r_img = requests.get(f"{BASE_URL}{img_url}", timeout=30)
    assert r_img.status_code == 200
    assert r_img.headers.get("content-type", "").startswith("image/")

    # PUT status to reviewing
    r = requests.put(f"{API}/quotes/{qid}", headers=auth, json={"status": "reviewing"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["status"] == "reviewing"

    # Verify persistence via GET list
    r = requests.get(f"{API}/quotes", headers=auth, timeout=30)
    q2 = [x for x in r.json() if x["id"] == qid][0]
    assert q2["status"] == "reviewing"

    # DELETE
    r = requests.delete(f"{API}/quotes/{qid}", headers=auth, timeout=30)
    assert r.status_code == 200

    r = requests.get(f"{API}/quotes", headers=auth, timeout=30)
    assert not any(x["id"] == qid for x in r.json())


def test_quotes_list_requires_auth():
    r = requests.get(f"{API}/quotes", timeout=30)
    assert r.status_code == 401


def test_analytics_overview_has_quote_counts(auth):
    r = requests.get(f"{API}/analytics/overview", headers=auth, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "total_quotes" in d
    assert "new_quotes" in d
    assert isinstance(d["total_quotes"], int)
    assert isinstance(d["new_quotes"], int)
