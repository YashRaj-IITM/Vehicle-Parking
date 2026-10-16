def test_create_lot_creates_spots(api, admin, lot_id):
    spots = api.get(f"/api/admin/parking_lots/{lot_id}/spots", admin).get_json()["spots"]
    assert [s["spot_number"] for s in spots] == ["P1", "P2"]


def test_lot_validation(api, admin):
    r = api.post("/api/admin/parking_lots", admin, json={"prime_location_name": "X"})
    assert r.status_code == 400
    r = api.post("/api/admin/parking_lots", admin, json={
        "prime_location_name": "Mall", "price_per_hour": -5, "address": "Road",
        "pin_code": "560001", "maximum_number_of_spots": 3})
    assert r.status_code == 400


def test_read_update_and_search(api, admin, lot_id):
    assert api.get(f"/api/admin/parking_lots/{lot_id}", admin).status_code == 200
    r = api.put(f"/api/admin/parking_lots/{lot_id}", admin, json={"price_per_hour": 99, "maximum_number_of_spots": 4})
    assert r.status_code == 200 and r.get_json()["lot"]["price_per_hour"] == 99
    assert len(api.get(f"/api/admin/parking_lots/{lot_id}/spots", admin).get_json()["spots"]) == 4
    assert len(api.get("/api/admin/parking_lots?q=mall", admin).get_json()) == 1
    assert api.get("/api/admin/parking_lots?q=zzz", admin).get_json() == []


def test_unknown_lot_is_404(api, admin):
    assert api.get("/api/admin/parking_lots/999", admin).status_code == 404
    assert api.put("/api/admin/parking_lots/999", admin, json={}).status_code == 404
    assert api.delete("/api/admin/parking_lots/999", admin).status_code == 404


def test_delete_lot(api, admin, lot_id):
    assert api.delete(f"/api/admin/parking_lots/{lot_id}", admin).status_code == 200
    assert api.get(f"/api/admin/parking_lots/{lot_id}", admin).status_code == 404


def test_cannot_delete_lot_or_spot_while_occupied(api, admin, user, lot_id):
    api.post("/api/user/reserve", user, json={"lot_id": lot_id})
    assert api.delete(f"/api/admin/parking_lots/{lot_id}", admin).status_code == 400
    spots = api.get(f"/api/admin/parking_lots/{lot_id}/spots", admin).get_json()["spots"]
    occupied = next(s for s in spots if s["status"] == "O")
    assert api.delete(f"/api/admin/spots/{occupied['id']}", admin).status_code == 400
    assert occupied["current_reservation"]["user_full_name"] == "Test User"


def test_shrink_blocked_only_when_occupied_spot_would_be_removed(api, admin, user, user2, make_lot):
    lot = make_lot(spots=3)
    api.post("/api/user/reserve", user, json={"lot_id": lot})          # gets P1
    assert api.put(f"/api/admin/parking_lots/{lot}", admin, json={"maximum_number_of_spots": 1}).status_code == 200
    # lot has 1 spot now, taken by `user`
    assert api.post("/api/user/reserve", user2, json={"lot_id": lot}).status_code == 400


def test_shrink_refused_when_highest_spot_occupied(api, admin, user, user2, make_lot):
    lot = make_lot(spots=3)
    api.post("/api/user/reserve", user, json={"lot_id": lot})
    api.post("/api/user/reserve", user2, json={"lot_id": lot})          # gets P2
    assert api.put(f"/api/admin/parking_lots/{lot}", admin, json={"maximum_number_of_spots": 1}).status_code == 400


def test_delete_free_spot_updates_maximum(api, admin, lot_id):
    spots = api.get(f"/api/admin/parking_lots/{lot_id}/spots", admin).get_json()["spots"]
    assert api.delete(f"/api/admin/spots/{spots[-1]['id']}", admin).status_code == 200
    assert api.get(f"/api/admin/parking_lots/{lot_id}", admin).get_json()["maximum_number_of_spots"] == 1


def test_deleted_lot_disappears_but_history_stays(api, admin, user, make_lot):
    lot = make_lot(spots=1)
    rid = api.post("/api/user/reserve", user, json={"lot_id": lot}).get_json()["reservation"]["id"]
    api.post("/api/user/release", user, json={"reservation_id": rid})
    assert api.delete(f"/api/admin/parking_lots/{lot}", admin).status_code == 200

    assert api.get("/api/admin/parking_lots", admin).get_json() == []
    assert api.get("/api/user/parking_lots", user).get_json() == []
    assert api.post("/api/user/reserve", user, json={"lot_id": lot}).status_code == 404
    mine = api.get("/api/user/my_reservations", user).get_json()
    assert len(mine) == 1 and mine[0]["lot_name"] == "City Mall"      # history is intact
    stats = api.get("/api/admin/stats", admin).get_json()
    assert stats["totalLots"] == 0 and stats["totalSpots"] == 0        # deleted lots are not counted


def test_spots_with_history_cannot_be_removed(api, admin, user, user2, make_lot):
    lot = make_lot(spots=2)
    # both park at the same time, so user gets P1 and user2 gets P2; then both leave
    booked = [(t, api.post("/api/user/reserve", t, json={"lot_id": lot}).get_json()["reservation"]["id"])
              for t in (user, user2)]
    for token, rid in booked:
        api.post("/api/user/release", token, json={"reservation_id": rid})
    spots = api.get(f"/api/admin/parking_lots/{lot}/spots", admin).get_json()["spots"]
    assert api.delete(f"/api/admin/spots/{spots[0]['id']}", admin).status_code == 400
    assert api.put(f"/api/admin/parking_lots/{lot}", admin, json={"maximum_number_of_spots": 1}).status_code == 400
    assert len(api.get(f"/api/admin/parking_lots/{lot}/spots", admin).get_json()["spots"]) == 2
