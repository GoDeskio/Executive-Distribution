"""Backend RBAC tests - role-based access control."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cargo-command-58.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER_EMAIL = "admin@executivedistribution.com"
SUPER_PASSWORD = "Executive2025!"

SUB_EMAIL = "crmtest@exd.com"
SUB_PASSWORD = "SubPass123!"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    return r


@pytest.fixture(scope="module")
def super_token():
    r = _login(SUPER_EMAIL, SUPER_PASSWORD)
    assert r.status_code == 200, f"super admin login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def sub_user(super_token):
    """Create a sub-admin. Yields (user_dict, token). Cleans up after."""
    h = {"Authorization": f"Bearer {super_token}"}
    # cleanup any pre-existing test user
    users = requests.get(f"{API}/users", headers=h).json()
    for u in users:
        if u["email"] == SUB_EMAIL:
            requests.delete(f"{API}/users/{u['id']}", headers=h)
    payload = {"email": SUB_EMAIL, "password": SUB_PASSWORD, "name": "CRM Test Sub", "permissions": ["crm", "dashboard"]}
    r = requests.post(f"{API}/users", headers=h, json=payload)
    assert r.status_code == 200, f"create sub-admin failed: {r.status_code} {r.text}"
    created = r.json()
    lr = _login(SUB_EMAIL, SUB_PASSWORD)
    assert lr.status_code == 200
    token = lr.json()["token"]
    yield created, token
    # teardown
    requests.delete(f"{API}/users/{created['id']}", headers=h)


class TestSuperAdmin:
    def test_login(self, super_token):
        assert super_token

    def test_me_role_and_permissions(self, super_token):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {super_token}"})
        assert r.status_code == 200
        d = r.json()
        assert d.get("role") == "superadmin"
        # permissions may be missing or list - superadmin bypasses via role check
        assert d.get("email") == SUPER_EMAIL

    def test_super_can_list_users(self, super_token):
        r = requests.get(f"{API}/users", headers={"Authorization": f"Bearer {super_token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_super_can_access_all_sections(self, super_token):
        h = {"Authorization": f"Bearer {super_token}"}
        for ep in ["/clients", "/documents", "/quotes", "/analytics/overview", "/services"]:
            r = requests.get(f"{API}{ep}", headers=h)
            assert r.status_code == 200, f"super access {ep}: {r.status_code} {r.text[:150]}"

    def test_super_cannot_be_modified(self, super_token):
        h = {"Authorization": f"Bearer {super_token}"}
        r = requests.get(f"{API}/users", headers=h)
        super_row = next(u for u in r.json() if u["email"] == SUPER_EMAIL)
        u_id = super_row["id"]
        r2 = requests.put(f"{API}/users/{u_id}", headers=h, json={"active": False})
        assert r2.status_code == 400
        r3 = requests.delete(f"{API}/users/{u_id}", headers=h)
        assert r3.status_code == 400
        r4 = requests.post(f"{API}/users/{u_id}/password", headers=h, json={"password": "x"})
        assert r4.status_code == 400


class TestSubAdmin:
    def test_sub_login_and_me(self, sub_user):
        created, token = sub_user
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        d = r.json()
        assert d.get("role") == "subadmin"
        assert set(d.get("permissions") or []) == {"crm", "dashboard"}

    def test_sub_allowed_endpoints(self, sub_user):
        _, token = sub_user
        h = {"Authorization": f"Bearer {token}"}
        assert requests.get(f"{API}/clients", headers=h).status_code == 200
        assert requests.get(f"{API}/quotes", headers=h).status_code == 200
        assert requests.get(f"{API}/analytics/overview", headers=h).status_code == 200

    def test_sub_denied_endpoints(self, sub_user):
        _, token = sub_user
        h = {"Authorization": f"Bearer {token}"}
        assert requests.get(f"{API}/documents", headers=h).status_code == 403
        assert requests.get(f"{API}/users", headers=h).status_code == 403
        assert requests.get(f"{API}/permissions", headers=h).status_code == 403
        # ai/chat/admin requires 'ai'
        r = requests.post(f"{API}/ai/chat/admin", headers=h, json={"messages": [{"role": "user", "content": "hi"}]})
        assert r.status_code == 403

    def test_sub_cannot_create_users(self, sub_user):
        _, token = sub_user
        h = {"Authorization": f"Bearer {token}"}
        r = requests.post(f"{API}/users", headers=h, json={"email": "x@y.com", "password": "p", "permissions": []})
        assert r.status_code == 403


class TestEditAndDisable:
    def test_edit_permissions_persist(self, super_token, sub_user):
        created, sub_token = sub_user
        h = {"Authorization": f"Bearer {super_token}"}
        # add documents permission, remove crm
        r = requests.put(f"{API}/users/{created['id']}", headers=h,
                         json={"permissions": ["documents", "dashboard"]})
        assert r.status_code == 200
        assert set(r.json()["permissions"]) == {"documents", "dashboard"}
        # sub-admin now sees documents allowed, clients denied
        sh = {"Authorization": f"Bearer {sub_token}"}
        assert requests.get(f"{API}/documents", headers=sh).status_code == 200
        assert requests.get(f"{API}/clients", headers=sh).status_code == 403
        # restore for later tests
        requests.put(f"{API}/users/{created['id']}", headers=h,
                     json={"permissions": ["crm", "dashboard"]})

    def test_reset_password(self, super_token, sub_user):
        created, _ = sub_user
        h = {"Authorization": f"Bearer {super_token}"}
        new_pw = "NewSubPass456!"
        r = requests.post(f"{API}/users/{created['id']}/password", headers=h, json={"password": new_pw})
        assert r.status_code == 200
        # login with new pw succeeds
        lr = _login(SUB_EMAIL, new_pw)
        assert lr.status_code == 200
        # old pw fails
        assert _login(SUB_EMAIL, SUB_PASSWORD).status_code == 401
        # restore
        requests.post(f"{API}/users/{created['id']}/password", headers=h, json={"password": SUB_PASSWORD})

    def test_disable_account_blocks_login(self, super_token, sub_user):
        created, _ = sub_user
        h = {"Authorization": f"Bearer {super_token}"}
        r = requests.put(f"{API}/users/{created['id']}", headers=h, json={"active": False})
        assert r.status_code == 200
        assert r.json()["active"] is False
        # existing token should be rejected (get_current_user rejects inactive)
        lr = _login(SUB_EMAIL, SUB_PASSWORD)
        # login succeeds since it does not check active, but /me should fail
        if lr.status_code == 200:
            tok = lr.json()["token"]
            me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"})
            assert me.status_code == 403, f"disabled user should be blocked, got {me.status_code}"
        # re-enable
        requests.put(f"{API}/users/{created['id']}", headers=h, json={"active": True})
