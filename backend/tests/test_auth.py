def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_protected_routes_require_token(api):
    assert api.get("/api/user/parking_lots").status_code == 401
    assert api.get("/api/admin/stats").status_code == 401
    assert api.get("/api/admin/stats", "garbage-token").status_code == 401


def test_register_and_login(api):
    r = api.register("new@example.com", vehicle_number="ka01ab1234")
    assert r.status_code == 201
    r = api.login("new@example.com", "password1")
    body = r.get_json()
    assert r.status_code == 200 and body["token"]
    assert body["user"]["role"] == "user" and body["user"]["is_admin"] is False


def test_register_validation(api):
    assert api.register("bad-email").status_code == 400
    assert api.register("a@example.com", password="123").status_code == 400
    assert api.post("/api/auth/register", json={"email": "a@example.com"}).status_code == 400
    assert api.post("/api/auth/register", data="not json").status_code == 400


def test_duplicate_email_rejected(api):
    assert api.register("dup@example.com").status_code == 201
    assert api.register("DUP@example.com").status_code == 400


def test_bad_credentials(api):
    api.register("x@example.com")
    assert api.login("x@example.com", "wrong-password").status_code == 401
    assert api.login("nobody@example.com", "password1").status_code == 401


def test_admin_login_has_admin_role(api):
    body = api.login("admin@example.com", "admin123").get_json()
    assert body["user"]["is_admin"] is True


def test_me_endpoint(api, user):
    assert api.get("/api/auth/me", user).get_json()["user"]["email"] == "user1@example.com"


def test_logout_invalidates_token(api, user):
    assert api.post("/api/auth/logout", user).status_code == 200
    assert api.get("/api/user/profile", user).status_code == 401


def test_role_separation(api, admin, user):
    assert api.get("/api/admin/stats", user).status_code == 403
    assert api.get("/api/user/parking_lots", admin).status_code == 403
