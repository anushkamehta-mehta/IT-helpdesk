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


def test_workflow_resolve_and_employee_close(make_client):
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
    t = it.patch(f"/api/tickets/{t['id']}", json={"status": "On Hold"}).json()
    assert t["status"] == "On Hold"

    # cannot resolve without resolution notes
    assert it.patch(f"/api/tickets/{t['id']}", json={"status": "Resolved"}).status_code == 422
    t = it.patch(f"/api/tickets/{t['id']}", json={"status": "Resolved", "resolution_notes": "Replaced SSD"}).json()
    assert t["status"] == "Resolved" and t["resolution_notes"] == "Replaced SSD" and t["closed_at"] is None

    # IT can neither set Closed nor call the close endpoint
    assert it.patch(f"/api/tickets/{t['id']}", json={"status": "Closed"}).status_code == 422
    assert it.post(f"/api/tickets/{t['id']}/close").status_code == 403

    t = emp.post(f"/api/tickets/{t['id']}/close").json()
    assert t["status"] == "Closed" and t["closed_at"]

    # closed tickets are frozen
    assert it.patch(f"/api/tickets/{t['id']}", json={"priority": "High"}).status_code == 409
    assert emp.post(f"/api/tickets/{t['id']}/comments", json={"body": "thanks"}).status_code == 409
    assert emp.post(f"/api/tickets/{t['id']}/close").status_code == 409


def test_employee_requests_changes_on_resolved_ticket(make_client):
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(it, "ivan@acme.com")
    ivan_id = it.get("/api/users/it-team").json()[0]["id"]
    t = emp.post("/api/tickets", json=NEW).json()

    # only a Resolved ticket can be sent back
    assert emp.post(f"/api/tickets/{t['id']}/reopen", json={"body": "still broken"}).status_code == 409
    it.patch(f"/api/tickets/{t['id']}", json={"assigned_to": ivan_id, "resolution_notes": "Rebooted"})
    it.patch(f"/api/tickets/{t['id']}", json={"status": "Resolved"})

    assert emp.post(f"/api/tickets/{t['id']}/reopen", json={"body": "  "}).status_code == 422
    assert it.post(f"/api/tickets/{t['id']}/reopen", json={"body": "x"}).status_code == 403
    t = emp.post(f"/api/tickets/{t['id']}/reopen", json={"body": "Still won't boot"}).json()
    assert t["status"] == "In Progress" and t["assignee"]["id"] == ivan_id
    assert t["comments"][-1]["body"] == "Still won't boot"


def test_admin_cannot_close_ticket(make_client):
    emp, admin = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(admin, "admin@acme.com")
    t = emp.post("/api/tickets", json=NEW).json()
    assert admin.post(f"/api/tickets/{t['id']}/close").status_code == 403
    assert admin.patch(f"/api/tickets/{t['id']}", json={"status": "Closed"}).status_code == 403


def test_assignment_sets_status_to_assigned(make_client):
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(it, "ivan@acme.com")
    ivan_id, priya_id = [u["id"] for u in it.get("/api/users/it-team").json()][:2]
    t = emp.post("/api/tickets", json=NEW).json()

    # assign and start work in one save
    t = it.patch(f"/api/tickets/{t['id']}", json={"assigned_to": ivan_id, "status": "In Progress"}).json()
    assert t["status"] == "In Progress"
    # re-saving the same assignee leaves the status alone
    assert it.patch(f"/api/tickets/{t['id']}", json={"assigned_to": ivan_id}).json()["status"] == "In Progress"
    # reassigning to someone else puts it back to Assigned
    t = it.patch(f"/api/tickets/{t['id']}", json={"assigned_to": priya_id}).json()
    assert t["status"] == "Assigned" and t["assignee"]["id"] == priya_id


def test_invalid_transitions(make_client):
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com")
    login(it, "ivan@acme.com")
    t = emp.post("/api/tickets", json=NEW).json()
    # an Open ticket must be assigned before its status can change
    for s in ("Assigned", "In Progress", "On Hold", "Resolved", "Closed"):
        assert it.patch(f"/api/tickets/{t['id']}", json={"status": s}).status_code == 422
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


def test_resolving_emails_the_requester(make_client, monkeypatch):
    from app.services import notifications

    sent = []
    monkeypatch.setattr(notifications, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    emp, it = make_client(), make_client()
    register_and_login(emp, "alice@acme.com", "Alice")
    login(it, "ivan@acme.com")
    ivan_id = it.get("/api/users/it-team").json()[0]["id"]
    t = emp.post("/api/tickets", json=NEW).json()

    it.patch(f"/api/tickets/{t['id']}", json={"assigned_to": ivan_id, "status": "In Progress"})
    assert sent == []  # no email for other status changes
    it.patch(f"/api/tickets/{t['id']}", json={"status": "Resolved", "resolution_notes": "Replaced the SSD"})
    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == "alice@acme.com" and f"#{t['id']}" in subject
    assert "Replaced the SSD" in body and NEW["description"] in body and "Ivan IT" in body
    assert f"/tickets/{t['id']}" in body

    it.patch(f"/api/tickets/{t['id']}", json={"priority": "Low"})
    assert len(sent) == 1  # saving a Resolved ticket again does not re-send

    # sent back by the employee and resolved again: emailed again
    emp.post(f"/api/tickets/{t['id']}/reopen", json={"body": "Still slow"})
    it.patch(f"/api/tickets/{t['id']}", json={"status": "Resolved"})
    assert len(sent) == 2


def test_email_skipped_when_smtp_not_configured(monkeypatch):
    import smtplib

    from app.core.config import Settings
    from app.services import notifications

    monkeypatch.setattr(notifications, "get_settings", lambda: Settings(smtp_host=""))
    monkeypatch.setattr(smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not connect")))
    notifications.send_email("a@acme.com", "s", "b")


def test_session_is_renewed_while_active_and_401_messages(make_client):
    from datetime import datetime, timedelta, timezone

    import jwt

    from app.core.config import get_settings

    c = make_client()
    user = register_and_login(c, "alice@acme.com")
    # A fresh token is not reissued on every request.
    r = c.get("/api/auth/me")
    assert r.status_code == 200 and "set-cookie" not in r.headers

    # A token with only 5 minutes left is renewed on the next request.
    now = datetime.now(timezone.utc)
    old = jwt.encode({"sub": str(user["id"]), "role": "employee", "iat": now - timedelta(minutes=55),
                      "exp": now + timedelta(minutes=5)}, get_settings().jwt_secret, algorithm="HS256")
    c.cookies.clear()
    c.cookies.set("access_token", old)
    r = c.get("/api/tickets")
    assert r.status_code == 200 and "access_token=" in r.headers["set-cookie"]
    assert old not in r.headers["set-cookie"]

    # Expired token vs. no cookie at all give different, clear messages.
    expired = jwt.encode({"sub": str(user["id"]), "role": "employee", "exp": now - timedelta(minutes=1)},
                         get_settings().jwt_secret, algorithm="HS256")
    c.cookies.clear()
    c.cookies.set("access_token", expired)
    r = c.get("/api/tickets")
    assert r.status_code == 401 and "expired" in r.json()["detail"]
    c.cookies.clear()
    r = c.get("/api/tickets")
    assert r.status_code == 401 and "logged out" in r.json()["detail"]


def test_brevo_used_when_api_key_set(monkeypatch):
    import json

    from app.core.config import Settings
    from app.services import notifications

    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.headers, json.loads(request.data)))
        return FakeResponse()

    monkeypatch.setattr(notifications, "get_settings",
                        lambda: Settings(brevo_api_key="key-123", smtp_from="helpdesk@acme.com", smtp_host="smtp.example.com"))
    monkeypatch.setattr(notifications.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(notifications.smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(AssertionError("SMTP used")))

    notifications.send_email("alice@acme.com", "Ticket #1 resolved", "Fixed")
    url, headers, payload = calls[0]
    assert url == notifications.BREVO_URL and headers["Api-key"] == "key-123"
    assert payload["sender"]["email"] == "helpdesk@acme.com" and payload["to"] == [{"email": "alice@acme.com"}]
    assert payload["subject"] == "Ticket #1 resolved" and payload["textContent"] == "Fixed"
