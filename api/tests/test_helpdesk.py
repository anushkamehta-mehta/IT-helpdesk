from tests.helpers import login, register_and_login

NEW = {"title": "Laptop broken", "description": "Won't boot", "category_id": 1, "priority": "High"}


def test_csrf_header_required(make_client):
    c = make_client()
    r = c.post("/api/auth/login", json={"email": "a@b.com", "password": "x"}, headers={"X-Requested-With": ""})
    assert r.status_code == 403


def test_register_login_me_logout(make_client):
    c = make_client()
    user = register_and_login(c, "alice@acme.com", "Alice")
    assert user["role"] == "employee"
    assert c.get("/api/auth/me").json()["email"] == "alice@acme.com"
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401


def test_duplicate_register_and_bad_login(make_client):
    c = make_client()
    register_and_login(c, "alice@acme.com")
    dup = c.post("/api/auth/register", json={"full_name": "A", "email": "ALICE@acme.com", "password": "password123"})
    assert dup.status_code == 409
    bad = c.post("/api/auth/login", json={"email": "alice@acme.com", "password": "wrong-password"})
    assert bad.status_code == 401


def test_register_cannot_choose_role(make_client):
    c = make_client()
    r = c.post("/api/auth/register", json={"full_name": "X", "email": "x@acme.com", "password": "password123", "role": "it_team"})
    assert r.status_code == 201 and r.json()["role"] == "employee"


def test_employee_sees_only_own_tickets(make_client):
    alice, bob = make_client(), make_client()
    register_and_login(alice, "alice@acme.com")
    register_and_login(bob, "bob@acme.com")
    t = alice.post("/api/tickets", json=NEW).json()
    assert len(alice.get("/api/tickets").json()) == 1
    assert bob.get("/api/tickets").json() == []
    assert bob.get(f"/api/tickets/{t['id']}").status_code == 404
    assert bob.post(f"/api/tickets/{t['id']}/comments", json={"body": "hi"}).status_code == 404


def test_employee_cannot_use_it_endpoints(make_client):
    c = make_client()
    register_and_login(c, "alice@acme.com")
    t = c.post("/api/tickets", json=NEW).json()
    assert c.patch(f"/api/tickets/{t['id']}", json={"status": "Closed"}).status_code == 403
    assert c.patch(f"/api/tickets/{t['id']}", json={"assigned_to": 1}).status_code == 403
    assert c.get("/api/users/it-team").status_code == 403


def test_it_workflow_to_close(make_client):
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(it, "ivan@acme.com")
    t = emp.post("/api/tickets", json=NEW).json()
    assert t["status"] == "Open"

    ivan_id = it.get("/api/users/it-team").json()[0]["id"]
    # assigning an Open ticket moves it to Assigned
    t = it.patch(f"/api/tickets/{t['id']}", json={"assigned_to": ivan_id}).json()
    assert t["status"] == "Assigned" and t["assignee"]["id"] == ivan_id

    t = it.patch(f"/api/tickets/{t['id']}", json={"status": "In Progress", "priority": "Low"}).json()
    assert t["status"] == "In Progress" and t["priority"] == "Low"

    # cannot close without resolution notes
    assert it.patch(f"/api/tickets/{t['id']}", json={"status": "Closed"}).status_code == 422
    t = it.patch(f"/api/tickets/{t['id']}", json={"status": "Closed", "resolution_notes": "Replaced SSD"}).json()
    assert t["status"] == "Closed" and t["closed_at"] and t["resolution_notes"] == "Replaced SSD"

    # closed tickets are frozen
    assert it.patch(f"/api/tickets/{t['id']}", json={"priority": "High"}).status_code == 409
    assert emp.post(f"/api/tickets/{t['id']}/comments", json={"body": "thanks"}).status_code == 409


def test_invalid_transitions(make_client):
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(it, "ivan@acme.com")
    t = emp.post("/api/tickets", json=NEW).json()
    # Open -> In Progress is not allowed, and Assigned needs an assignee
    assert it.patch(f"/api/tickets/{t['id']}", json={"status": "In Progress"}).status_code == 422
    assert it.patch(f"/api/tickets/{t['id']}", json={"status": "Assigned"}).status_code == 422
    assert it.patch(f"/api/tickets/{t['id']}", json={"assigned_to": 9999}).status_code == 422


def test_comments_and_search_filter(make_client):
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(it, "ivan@acme.com")
    a = emp.post("/api/tickets", json=NEW).json()
    emp.post("/api/tickets", json={**NEW, "title": "VPN issue", "priority": "Low"})

    d = emp.post(f"/api/tickets/{a['id']}/comments", json={"body": "More info"}).json()
    assert d["comments"][0]["body"] == "More info"
    d = it.post(f"/api/tickets/{a['id']}/comments", json={"body": "On it"}).json()
    assert len(d["comments"]) == 2

    assert len(it.get("/api/tickets").json()) == 2
    assert [t["title"] for t in it.get("/api/tickets", params={"q": "vpn"}).json()] == ["VPN issue"]
    assert len(it.get("/api/tickets", params={"priority": "High"}).json()) == 1
    assert len(it.get("/api/tickets", params={"unassigned": "true"}).json()) == 2


def test_owner_can_edit_and_delete_ticket(make_client):
    alice, bob = make_client(), make_client()
    register_and_login(alice, "alice@acme.com")
    register_and_login(bob, "bob@acme.com")
    t = alice.post("/api/tickets", json=NEW).json()
    alice.post(f"/api/tickets/{t['id']}/comments", json={"body": "any update?"})

    edited = alice.patch(f"/api/tickets/{t['id']}", json={"title": "Laptop dead", "priority": "Low"}).json()
    assert edited["title"] == "Laptop dead" and edited["priority"] == "Low"
    assert edited["description"] == NEW["description"]
    assert alice.patch(f"/api/tickets/{t['id']}", json={"title": "  "}).status_code == 422
    assert alice.patch(f"/api/tickets/{t['id']}", json={"category_id": 999}).status_code == 422

    # Other employees can neither edit nor delete it.
    assert bob.patch(f"/api/tickets/{t['id']}", json={"title": "x"}).status_code == 404
    assert bob.delete(f"/api/tickets/{t['id']}").status_code == 404

    assert alice.delete(f"/api/tickets/{t['id']}").status_code == 204
    assert alice.get(f"/api/tickets/{t['id']}").status_code == 404
    assert alice.get("/api/tickets").json() == []


def test_it_can_edit_and_delete_any_ticket(make_client):
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(it, "ivan@acme.com")
    t = emp.post("/api/tickets", json=NEW).json()
    assert it.patch(f"/api/tickets/{t['id']}", json={"description": "Fan noise"}).json()["description"] == "Fan noise"
    assert it.delete(f"/api/tickets/{t['id']}").status_code == 204
    assert emp.get("/api/tickets").json() == []
    assert it.delete(f"/api/tickets/{t['id']}").status_code == 404
