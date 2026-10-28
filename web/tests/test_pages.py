import os

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")

import pytest

from app import create_app


@pytest.fixture()
def client():
    return create_app().test_client()


@pytest.mark.parametrize("path", ["/login", "/register", "/tickets", "/tickets/new", "/tickets/5", "/it/tickets", "/admin"])
def test_pages_render(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert "Content-Security-Policy" in r.headers


def test_root_redirects_to_login(client):
    r = client.get("/")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_bad_ticket_id_is_404(client):
    assert client.get("/tickets/abc").status_code == 404
