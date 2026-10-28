from tests.helpers import login, register_and_login

NEW_IT = {"full_name": "Tara Tech", "email": "Tara@Acme.com", "password": "password123", "role": "it_team"}


def test_only_admin_can_manage_users(make_client):
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(it, "ivan@acme.com")
    for c in (emp, it):
        assert c.get("/api/admin/users").status_code == 403
        assert c.post("/api/admin/users", json=NEW_IT).status_code == 403
    assert make_client().get("/api/admin/users").status_code == 401


def test_admin_creates_users_with_roles(make_client):
    admin = make_client()
    login(admin, "admin@acme.com")
    r = admin.post("/api/admin/users", json=NEW_IT)
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "it_team" and r.json()["email"] == "tara@acme.com"
    assert admin.post("/api/admin/users", json=NEW_IT).status_code == 409
    assert admin.post("/api/admin/users", json={**NEW_IT, "email": "x@acme.com", "role": "boss"}).status_code == 422
    assert admin.post("/api/admin/users", json={**NEW_IT, "email": "y@acme.com", "password": "short"}).status_code == 422

    # The new IT member can log in, shows up in the assignee list and can be assigned work.
    tara = make_client()
    assert login(tara, "tara@acme.com", "password123")["role"] == "it_team"
    assert "Tara Tech" in [u["full_name"] for u in tara.get("/api/users/it-team").json()]

    emp = make_client()
    admin.post("/api/admin/users", json={"full_name": "Eve", "email": "eve@acme.com", "password": "password123"})
    assert login(emp, "eve@acme.com")["role"] == "employee"
    emails = [u["email"] for u in admin.get("/api/admin/users").json()]
    assert {"tara@acme.com", "eve@acme.com", "admin@acme.com"} <= set(emails)


def test_admin_edits_deactivates_and_deletes(make_client):
    admin = make_client()
    login(admin, "admin@acme.com")
    u = admin.post("/api/admin/users", json=NEW_IT).json()

    r = admin.patch(f"/api/admin/users/{u['id']}", json={"role": "employee", "full_name": "Tara T", "password": "newpassword1"})
    assert r.status_code == 200 and r.json()["role"] == "employee" and r.json()["full_name"] == "Tara T"
    assert login(make_client(), "tara@acme.com", "newpassword1")["role"] == "employee"
    assert admin.patch(f"/api/admin/users/{u['id']}", json={"email": "ivan@acme.com"}).status_code == 409

    assert admin.patch(f"/api/admin/users/{u['id']}", json={"is_active": False}).json()["is_active"] is False
    r = make_client().post("/api/auth/login", json={"email": "tara@acme.com", "password": "newpassword1"})
    assert r.status_code == 403 and "blocked" in r.json()["detail"]
    # A wrong password still gets the generic message, so blocked accounts can't be probed.
    r = make_client().post("/api/auth/login", json={"email": "tara@acme.com", "password": "wrong-password"})
    assert r.status_code == 401 and "blocked" not in r.json()["detail"]

    assert admin.delete(f"/api/admin/users/{u['id']}").status_code == 204
    assert admin.patch(f"/api/admin/users/{u['id']}", json={"is_active": True}).status_code == 404


def test_admin_cannot_lock_self_out_or_delete_users_with_history(make_client):
    admin, emp = make_client(), make_client()
    me = login(admin, "admin@acme.com")
    assert admin.patch(f"/api/admin/users/{me['id']}", json={"role": "employee"}).status_code == 422
    assert admin.patch(f"/api/admin/users/{me['id']}", json={"is_active": False}).status_code == 422
    assert admin.delete(f"/api/admin/users/{me['id']}").status_code == 422
    assert admin.patch(f"/api/admin/users/{me['id']}", json={"full_name": "Ada A"}).status_code == 200

    alice = register_and_login(emp, "alice@acme.com")
    emp.post("/api/tickets", json={"title": "t", "description": "d", "category_id": 1})
    assert admin.delete(f"/api/admin/users/{alice['id']}").status_code == 409
    assert admin.patch(f"/api/admin/users/{alice['id']}", json={"is_active": False}).status_code == 200
