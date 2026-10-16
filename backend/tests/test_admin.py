from datetime import timedelta

from extensions import db
from models import Reservation, utcnow


def test_stats_shape(api, admin, user, lot_id):
    api.post("/api/user/reserve", user, json={"lot_id": lot_id})
    s = api.get("/api/admin/stats", admin).get_json()
    assert s["totalLots"] == 1 and s["totalSpots"] == 2
    assert s["occupiedSpots"] == 1 and s["availableSpots"] == 1 and s["activeReservations"] == 1
    assert s["lotStats"][0]["name"] == "City Mall"
    assert [u["email"] for u in s["userStats"]] == ["user1@example.com"]   # admins excluded


def test_list_and_search_users(api, admin, user):
    assert len(api.get("/api/admin/users", admin).get_json()) == 2        # admin + user
    assert len(api.get("/api/admin/users?q=user1", admin).get_json()) == 1


def _user_id(api, admin, email="user1@example.com"):
    return next(u["id"] for u in api.get("/api/admin/users", admin).get_json() if u["email"] == email)


def test_blacklist_kills_token_and_blocks_login(api, admin, user):
    uid = _user_id(api, admin)
    assert api.put(f"/api/admin/users/{uid}/status", admin, json={"action": "blacklist"}).status_code == 200
    assert api.get("/api/user/profile", user).status_code == 401
    assert api.login("user1@example.com", "password1").status_code == 403
    assert api.put(f"/api/admin/users/{uid}/status", admin, json={"action": "activate"}).status_code == 200
    assert api.login("user1@example.com", "password1").status_code == 200


def test_status_validation_and_admin_protection(api, admin, user):
    uid = _user_id(api, admin)
    assert api.put(f"/api/admin/users/{uid}/status", admin, json={"action": "explode"}).status_code == 400
    admin_id = _user_id(api, admin, "admin@example.com")
    assert api.put(f"/api/admin/users/{admin_id}/status", admin, json={"action": "blacklist"}).status_code == 400
    assert api.delete(f"/api/admin/users/{admin_id}", admin).status_code == 400
    assert api.delete("/api/admin/users/999", admin).status_code == 404


def test_deleting_user_frees_their_spot(api, admin, user, make_lot):
    lot = make_lot(spots=1)
    api.post("/api/user/reserve", user, json={"lot_id": lot})
    assert api.delete(f"/api/admin/users/{_user_id(api, admin)}", admin).status_code == 200
    assert api.get(f"/api/admin/parking_lots/{lot}", admin).get_json()["available_spots"] == 1


def test_admin_reservation_list(api, admin, user, lot_id):
    api.post("/api/user/reserve", user, json={"lot_id": lot_id})
    assert len(api.get("/api/admin/reservations?active=true", admin).get_json()) == 1


def test_bulk_reminders_and_export_jobs(api, admin, user):
    uid = _user_id(api, admin)
    r = api.post("/api/admin/schedule_bulk_reminders", admin, json={"user_ids": [uid], "subject": "Hi", "body": "Park"})
    assert r.status_code == 200 and r.get_json()["count"] == 1
    assert api.post("/api/admin/schedule_bulk_reminders", admin, json={"user_ids": []}).status_code == 400
    assert api.post("/api/user/export", user).status_code == 202   # Celery runs eagerly in tests


def test_deleting_user_keeps_reservation_history(api, admin, user, make_lot):
    lot = make_lot(spots=1)
    api.post("/api/user/reserve", user, json={"lot_id": lot})
    uid = _user_id(api, admin)
    assert api.delete(f"/api/admin/users/{uid}", admin).status_code == 200

    rows = api.get("/api/admin/reservations", admin).get_json()
    assert len(rows) == 1                                   # the record survives
    assert rows[0]["is_active"] is False and rows[0]["leaving_timestamp"]   # open booking was closed
    assert rows[0]["user_name"] == "Deleted user"           # personal data is gone
    emails = [u["email"] for u in api.get("/api/admin/users", admin).get_json()]
    assert emails == ["admin@example.com"]                  # hidden from the user list
    assert api.get("/api/user/profile", user).status_code == 401        # old token is dead
    assert api.login("user1@example.com", "password1").status_code == 401
    assert api.delete(f"/api/admin/users/{uid}", admin).status_code == 404   # already deleted
    assert api.register("user1@example.com").status_code == 201        # the address can be reused


def test_revenue_survives_user_deletion(app, api, admin, user, make_lot):
    lot = make_lot(spots=1, price=10)
    rid = api.post("/api/user/reserve", user, json={"lot_id": lot}).get_json()["reservation"]["id"]
    api.post("/api/user/release", user, json={"reservation_id": rid})
    with app.app_context():
        r = db.session.get(Reservation, rid)
        r.parking_timestamp = utcnow() - timedelta(hours=2)
        r.leaving_timestamp = utcnow()
        db.session.commit()
    assert api.get("/api/admin/stats", admin).get_json()["totalRevenue"] == 20.0

    assert api.delete(f"/api/admin/users/{_user_id(api, admin)}", admin).status_code == 200
    stats = api.get("/api/admin/stats", admin).get_json()
    assert stats["totalRevenue"] == 20.0 and stats["userStats"] == []
