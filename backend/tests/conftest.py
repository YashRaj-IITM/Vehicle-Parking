import pytest

from app import create_app
from config import TestConfig

ADMIN = ("admin@example.com", "admin123")


@pytest.fixture()
def app(tmp_path):
    """A fresh app + in-memory database for every test (full isolation)."""
    app = create_app(TestConfig)
    app.config["EXPORT_DIR"] = str(tmp_path / "exports")   # keep generated CSV/HTML out of the repo
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


class Api:
    """Tiny helper: send requests with the Flask-Security token header."""

    def __init__(self, client):
        self.client = client

    def request(self, method, url, token=None, **kw):
        headers = {"Authentication-Token": token} if token else {}
        return getattr(self.client, method)(url, headers=headers, **kw)

    def get(self, url, token=None, **kw):
        return self.request("get", url, token, **kw)

    def post(self, url, token=None, **kw):
        return self.request("post", url, token, **kw)

    def put(self, url, token=None, **kw):
        return self.request("put", url, token, **kw)

    def delete(self, url, token=None, **kw):
        return self.request("delete", url, token, **kw)

    def register(self, email, password="password1", **extra):
        body = {"email": email, "password": password, "full_name": "Test User", **extra}
        return self.post("/api/auth/register", json=body)

    def login(self, email, password):
        return self.post("/api/auth/login", json={"email": email, "password": password})

    def token(self, email, password="password1"):
        r = self.login(email, password)
        assert r.status_code == 200, r.get_data(as_text=True)
        return r.get_json()["token"]

    def new_user(self, email, password="password1", **extra):
        assert self.register(email, password, **extra).status_code == 201
        return self.token(email, password)


@pytest.fixture()
def api(client):
    return Api(client)


@pytest.fixture()
def admin(api):
    return api.token(*ADMIN)


@pytest.fixture()
def user(api):
    return api.new_user("user1@example.com")


@pytest.fixture()
def user2(api):
    return api.new_user("user2@example.com")


@pytest.fixture()
def make_lot(api, admin):
    def _make(spots=2, price=40, name="City Mall"):
        r = api.post("/api/admin/parking_lots", admin, json={
            "prime_location_name": name, "price_per_hour": price,
            "address": "MG Road", "pin_code": "560001", "maximum_number_of_spots": spots})
        assert r.status_code == 201, r.get_data(as_text=True)
        return r.get_json()["id"]
    return _make


@pytest.fixture()
def lot_id(make_lot):
    return make_lot()
