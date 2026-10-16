from datetime import timedelta

from extensions import db
from models import Reservation, utcnow


def test_reserve_and_release_flow(api, user, lot_id):
    r = api.post("/api/user/reserve", user, json={"lot_id": lot_id})
    assert r.status_code == 201
    res = r.get_json()["reservation"]
    assert res["spot_number"] == "P1" and res["is_active"] is True

    r = api.post("/api/user/release", user, json={"reservation_id": res["id"]})
    assert r.status_code == 200 and r.get_json()["reservation"]["is_active"] is False
    assert api.post("/api/user/release", user, json={"reservation_id": res["id"]}).status_code == 400


def test_one_active_reservation_per_user(api, user, lot_id):
    assert api.post("/api/user/reserve", user, json={"lot_id": lot_id}).status_code == 201
    assert api.post("/api/user/reserve", user, json={"lot_id": lot_id}).status_code == 400


def test_full_lot_refuses_and_spots_are_never_double_booked(api, user, user2, make_lot):
    lot = make_lot(spots=1)
    assert api.post("/api/user/reserve", user, json={"lot_id": lot}).status_code == 201
    assert api.post("/api/user/reserve", user2, json={"lot_id": lot}).status_code == 400


def test_freed_spot_can_be_booked_again(api, user, user2, make_lot):
    lot = make_lot(spots=1)
    rid = api.post("/api/user/reserve", user, json={"lot_id": lot}).get_json()["reservation"]["id"]
    api.post("/api/user/release", user, json={"reservation_id": rid})
    assert api.post("/api/user/reserve", user2, json={"lot_id": lot}).status_code == 201


def test_reserve_validation(api, user):
    assert api.post("/api/user/reserve", user, json={}).status_code == 400
    assert api.post("/api/user/reserve", user, json={"lot_id": 999}).status_code == 404


def test_cannot_release_someone_elses_reservation(api, user, user2, lot_id):
    rid = api.post("/api/user/reserve", user, json={"lot_id": lot_id}).get_json()["reservation"]["id"]
    assert api.post("/api/user/release", user2, json={"reservation_id": rid}).status_code == 404


def test_cost_uses_price_frozen_at_booking(app, api, admin, user, make_lot):
    lot = make_lot(spots=1, price=50)
    rid = api.post("/api/user/reserve", user, json={"lot_id": lot}).get_json()["reservation"]["id"]
    api.put(f"/api/admin/parking_lots/{lot}", admin, json={"price_per_hour": 500})  # later price change
    with app.app_context():                     # pretend the user parked 2 hours ago
        r = db.session.get(Reservation, rid)
        r.parking_timestamp = utcnow() - timedelta(hours=2)
        db.session.commit()
    res = api.post("/api/user/release", user, json={"reservation_id": rid}).get_json()["reservation"]
    assert res["duration_hours"] == 2.0 and res["total_cost"] == 100.0


def test_history_stats_and_delete_record(api, user, lot_id):
    rid = api.post("/api/user/reserve", user, json={"lot_id": lot_id}).get_json()["reservation"]["id"]
    assert api.delete(f"/api/user/reservations/{rid}", user).status_code == 400   # still active
    api.post("/api/user/release", user, json={"reservation_id": rid})
    assert len(api.get("/api/user/my_reservations", user).get_json()) == 1
    assert api.get("/api/user/stats", user).get_json()["total_reservations"] == 1
    assert api.delete(f"/api/user/reservations/{rid}", user).status_code == 200
    assert api.get("/api/user/my_reservations", user).get_json() == []


def test_user_lot_search(api, user, lot_id):
    assert len(api.get("/api/user/parking_lots?q=city", user).get_json()) == 1
    assert api.get("/api/user/parking_lots?q=nothing", user).get_json() == []


def test_profile_update(api, user):
    r = api.put("/api/user/profile", user, json={"full_name": "New Name", "phone": "9999999999", "vehicle_number": "mh12xy9999"})
    assert r.status_code == 200
    me = api.get("/api/user/profile", user).get_json()
    assert me["full_name"] == "New Name" and me["vehicle_number"] == "MH12XY9999"
    assert api.put("/api/user/profile", user, json={"full_name": ""}).status_code == 400


def test_delete_account_rules(api, user, lot_id):
    rid = api.post("/api/user/reserve", user, json={"lot_id": lot_id}).get_json()["reservation"]["id"]
    assert api.delete("/api/user/account", user).status_code == 400   # must release first
    api.post("/api/user/release", user, json={"reservation_id": rid})
    assert api.delete("/api/user/account", user).status_code == 200
    assert api.login("user1@example.com", "password1").status_code == 401


# ----------------------------------------------------------- concurrency safety
def test_database_refuses_a_second_active_reservation_for_one_user(app, api, user, make_lot):
    """The guarantee lives in the database (partial unique index), not only in Python."""
    import pytest
    from sqlalchemy.exc import IntegrityError

    lot = make_lot(spots=2)
    api.post("/api/user/reserve", user, json={"lot_id": lot})
    with app.app_context():
        first = Reservation.query.filter_by(is_active=True).first()
        spare = db.session.query(__import__("models").ParkingSpot).filter_by(lot_id=lot, status="A").first()
        db.session.add(Reservation(spot_id=spare.id, user_id=first.user_id, parking_cost=1, is_active=True))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_parallel_requests_from_one_user_create_only_one_reservation(tmp_path):
    """8 simultaneous /reserve calls by the same user -> exactly one active reservation."""
    import threading

    from app import create_app
    from config import TestConfig

    class FileDb(TestConfig):
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(tmp_path / "race.db")

    app = create_app(FileDb)
    c = app.test_client()
    c.post("/api/auth/register", json={"email": "u@example.com", "password": "password1", "full_name": "Race User"})
    tok = c.post("/api/auth/login", json={"email": "u@example.com", "password": "password1"}).get_json()["token"]
    adm = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).get_json()["token"]
    lot = c.post("/api/admin/parking_lots", headers={"Authentication-Token": adm}, json={
        "prime_location_name": "Mall", "price_per_hour": 5, "address": "MG Road",
        "pin_code": "560001", "maximum_number_of_spots": 10}).get_json()["id"]

    codes = []

    def go():
        with app.test_client() as cl:
            codes.append(cl.post("/api/user/reserve", headers={"Authentication-Token": tok}, json={"lot_id": lot}).status_code)

    threads = [threading.Thread(target=go) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    mine = c.get("/api/user/my_reservations", headers={"Authentication-Token": tok}).get_json()
    assert sum(r["is_active"] for r in mine) == 1
    assert codes.count(201) == 1
    # the spots claimed by the losing requests were given back
    assert c.get(f"/api/admin/parking_lots/{lot}", headers={"Authentication-Token": adm}).get_json()["occupied_spots"] == 1


def test_every_free_spot_is_considered_not_just_the_first_few(api, make_lot):
    lot = make_lot(spots=8)
    tokens = [api.new_user(f"car{i}@example.com") for i in range(8)]
    codes = [api.post("/api/user/reserve", t, json={"lot_id": lot}).status_code for t in tokens]
    assert codes == [201] * 8                      # all 8 spots usable, none wrongly "full"
    assert api.post("/api/user/reserve", api.new_user("late@example.com"), json={"lot_id": lot}).status_code == 400
