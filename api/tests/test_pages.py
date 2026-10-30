import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.mark.parametrize("path", ["/login", "/register", "/tickets", "/tickets/new", "/tickets/5", "/it/tickets", "/admin"])
def test_pages_render(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "Content-Security-Policy" in r.headers


def test_root_redirects_to_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_bad_ticket_id_is_404(client):
    assert client.get("/tickets/abc").status_code == 404


def test_static_files_served(client):
    r = client.get("/static/css/style.css")
    assert r.status_code == 200 and "text/css" in r.headers["content-type"]
