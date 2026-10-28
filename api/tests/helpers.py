def login(client, email, password="password123"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def register_and_login(client, email, name="Emp"):
    r = client.post("/api/auth/register", json={"full_name": name, "email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    return login(client, email)
