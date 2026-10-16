from flask import Blueprint, jsonify, request

from extensions import db
from models import ParkingLot, ParkingSpot, Reservation, User, user_datastore, utcnow
from utils import ValidationError, error, json_body, number, text, token_roles

admin_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")
admin_only = token_roles("admin")


def _lot_fields(data, partial=False, lot=None):
    """Validate lot input. When partial=True missing keys keep the current value."""

    def pick(key, current=None):
        return data.get(key, current) if partial else data.get(key)

    return {
        "prime_location_name": text(pick("prime_location_name", lot and lot.prime_location_name),
                                    "Location name", min_len=2, max_len=200, required=True),
        "price_per_hour": number(pick("price_per_hour", lot and lot.price_per_hour),
                                 "Price per hour", lo=0.01, hi=100000, required=True),
        "address": text(pick("address", lot and lot.address), "Address", min_len=3, max_len=500, required=True),
        "pin_code": text(str(pick("pin_code", lot and lot.pin_code) or ""), "PIN code",
                         min_len=3, max_len=10, required=True),
        "maximum_number_of_spots": number(pick("maximum_number_of_spots", lot and lot.maximum_number_of_spots),
                                          "Number of spots", cast=int, lo=1, hi=500, required=True),
    }


def _live_lot(lot_id):
    """The lot with this id, or None when it does not exist or was deleted."""
    lot = db.session.get(ParkingLot, lot_id)
    return lot if lot and lot.deleted_at is None else None


def _live_spots():
    """Query over the spots of lots that have not been deleted."""
    return ParkingSpot.query.join(ParkingLot, ParkingSpot.lot_id == ParkingLot.id).filter(
        ParkingLot.deleted_at.is_(None)
    )


# ------------------------------------------------------------- parking lots
@admin_bp.get("/parking_lots")
@admin_only
def list_lots():
    q = (request.args.get("q") or "").strip()
    query = ParkingLot.live()
    if q:
        like = f"%{q}%"
        query = query.filter(
            ParkingLot.prime_location_name.ilike(like)
            | ParkingLot.address.ilike(like)
            | ParkingLot.pin_code.ilike(like)
        )
    return jsonify([l.to_dict() for l in query.order_by(ParkingLot.id).all()])


@admin_bp.post("/parking_lots")
@admin_only
def create_lot():
    f = _lot_fields(json_body())
    lot = ParkingLot(**f)
    db.session.add(lot)
    db.session.flush()
    db.session.add_all(
        ParkingSpot(lot_id=lot.id, spot_number=f"P{i}") for i in range(1, lot.maximum_number_of_spots + 1)
    )
    db.session.commit()
    return jsonify({"success": True, "id": lot.id, "lot": lot.to_dict()}), 201


@admin_bp.get("/parking_lots/<int:lot_id>")
@admin_only
def get_lot(lot_id):
    lot = _live_lot(lot_id)
    if not lot:
        return error("Parking lot not found", 404)
    return jsonify(lot.to_dict())


@admin_bp.put("/parking_lots/<int:lot_id>")
@admin_only
def update_lot(lot_id):
    lot = _live_lot(lot_id)
    if not lot:
        return error("Parking lot not found", 404)
    f = _lot_fields(json_body(), partial=True, lot=lot)

    new_max = f["maximum_number_of_spots"]
    current = ParkingSpot.query.filter_by(lot_id=lot.id).count()
    if new_max > current:
        db.session.add_all(
            ParkingSpot(lot_id=lot.id, spot_number=f"P{i}") for i in range(current + 1, new_max + 1)
        )
    elif new_max < current:
        doomed = (
            ParkingSpot.query.filter_by(lot_id=lot.id).order_by(ParkingSpot.id.desc()).limit(current - new_max).all()
        )
        if any(s.status != "A" for s in doomed):
            return error("Cannot reduce spots while some of the spots to be removed are occupied", 400)
        if Reservation.query.filter(Reservation.spot_id.in_([s.id for s in doomed])).first():
            return error("Cannot remove spots that have reservation history (records are kept)", 400)
        for s in doomed:
            db.session.delete(s)

    for key, value in f.items():
        setattr(lot, key, value)
    db.session.commit()
    return jsonify({"success": True, "lot": lot.to_dict()})


@admin_bp.delete("/parking_lots/<int:lot_id>")
@admin_only
def delete_lot(lot_id):
    lot = _live_lot(lot_id)
    if not lot:
        return error("Parking lot not found", 404)
    if ParkingSpot.query.filter_by(lot_id=lot.id, status="O").count():
        return error("Cannot delete lot while some spots are occupied", 400)
    # Soft delete: the lot disappears from every list, but its spots and all reservation
    # history stay in the database so past bills and revenue remain correct.
    lot.deleted_at = utcnow()
    db.session.commit()
    return jsonify({"success": True})


@admin_bp.get("/parking_lots/<int:lot_id>/spots")
@admin_only
def list_spots(lot_id):
    lot = _live_lot(lot_id)
    if not lot:
        return error("Parking lot not found", 404)
    result = []
    for s in ParkingSpot.query.filter_by(lot_id=lot.id).order_by(ParkingSpot.id).all():
        info = {
            "id": s.id,
            "spot_number": s.spot_number,
            "status": s.status,
            "is_available": s.is_available,
            "is_occupied": s.is_occupied,
        }
        if s.is_occupied:
            res = Reservation.query.filter_by(spot_id=s.id, is_active=True).first()
            if res:
                info["current_reservation"] = {
                    "id": res.id,
                    "user_id": res.user_id,
                    "user_full_name": res.user.full_name,
                    "vehicle_number": res.user.vehicle_number,
                    "parking_timestamp": res.to_dict()["parking_timestamp"],
                }
        result.append(info)
    return jsonify({"lot": {"id": lot.id, "name": lot.prime_location_name}, "spots": result})


@admin_bp.delete("/spots/<int:spot_id>")
@admin_only
def delete_spot(spot_id):
    spot = db.session.get(ParkingSpot, spot_id)
    if not spot:
        return error("Spot not found", 404)
    if spot.is_occupied:
        return error("Cannot delete an occupied spot", 400)
    if Reservation.query.filter_by(spot_id=spot.id).first():
        return error("Cannot delete a spot that has reservation history (records are kept)", 400)
    lot = spot.parking_lot
    if lot.maximum_number_of_spots <= 1:
        return error("A lot must keep at least one spot", 400)
    lot.maximum_number_of_spots -= 1
    db.session.delete(spot)
    db.session.commit()
    return jsonify({"success": True})


# -------------------------------------------------------------------- users
@admin_bp.get("/users")
@admin_only
def list_users():
    q = (request.args.get("q") or "").strip()
    query = User.query.filter(User.deleted_at.is_(None))
    if q:
        like = f"%{q}%"
        query = query.filter(
            User.full_name.ilike(like) | User.email.ilike(like) | User.vehicle_number.ilike(like)
        )
    return jsonify([u.to_dict() for u in query.order_by(User.id).all()])


@admin_bp.put("/users/<int:user_id>/status")
@admin_only
def set_user_status(user_id):
    user = db.session.get(User, user_id)
    if not user or user.is_deleted:
        return error("User not found", 404)
    if user.is_admin:
        return error("Admin accounts cannot be changed here", 400)
    action = json_body().get("action")
    if action not in ("blacklist", "activate"):
        raise ValidationError("action must be 'blacklist' or 'activate'")
    user.active = action == "activate"
    if not user.active:
        user_datastore.set_uniquifier(user)  # invalidates existing tokens immediately
    db.session.commit()
    return jsonify({"success": True, "user": user.to_dict()})


@admin_bp.delete("/users/<int:user_id>")
@admin_only
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.is_deleted:
        return error("User not found", 404)
    if user.is_admin:
        return error("Admin accounts cannot be deleted", 400)
    now = utcnow()
    for r in Reservation.query.filter_by(user_id=user.id, is_active=True).all():
        # close the open booking (so it is billed) and free the spot the user was holding
        r.leaving_timestamp = now
        r.is_active = False
        r.parking_spot.status = "A"
    user.anonymise()  # soft delete: reservation history is kept
    db.session.commit()
    return jsonify({"success": True})


# ------------------------------------------------------------- reservations
@admin_bp.get("/reservations")
@admin_only
def list_reservations():
    query = Reservation.query
    if request.args.get("active") == "true":
        query = query.filter_by(is_active=True)
    rows = query.order_by(Reservation.id.desc()).limit(500).all()
    return jsonify([r.to_dict() for r in rows])


# -------------------------------------------------------------------- stats
@admin_bp.get("/stats")
@admin_only
def stats():
    lot_stats = [
        {
            "id": l.id,
            "name": l.prime_location_name,
            "total_spots": l.maximum_number_of_spots,
            "available_spots": l.available_spots,
            "occupied_spots": l.occupied_spots,
            "price_per_hour": l.price_per_hour,
        }
        for l in ParkingLot.live().order_by(ParkingLot.id).all()
    ]
    user_stats, revenue = [], 0.0
    for u in User.query.order_by(User.id).all():
        if u.is_admin:
            continue
        done = [r for r in u.reservations if not r.is_active]
        spent = round(sum(r.total_cost for r in done), 2)
        revenue += spent  # deleted users still count: their past payments are real revenue
        if u.is_deleted:
            continue
        user_stats.append(
            {
                "id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "vehicle_number": u.vehicle_number,
                "total_reservations": len(u.reservations),
                "total_hours": round(sum(r.duration_hours for r in done), 2),
                "total_spent": spent,
            }
        )
    return jsonify(
        {
            "totalLots": len(lot_stats),
            "totalSpots": _live_spots().count(),
            "availableSpots": _live_spots().filter(ParkingSpot.status == "A").count(),
            "occupiedSpots": _live_spots().filter(ParkingSpot.status == "O").count(),
            "activeReservations": Reservation.query.filter_by(is_active=True).count(),
            "lotStats": lot_stats,
            "userStats": user_stats,
            "totalRevenue": round(revenue, 2),
        }
    )


# ---------------------------------------------------- bulk reminders (Celery)
@admin_bp.post("/schedule_bulk_reminders")
@admin_only
def schedule_bulk_reminders():
    from datetime import datetime, timezone

    data = json_body()
    ids = data.get("user_ids")
    if not isinstance(ids, list) or not ids:
        raise ValidationError("user_ids (a non-empty list) is required")
    subject = text(data.get("subject") or "Parking reminder", "Subject", max_len=200)
    body = text(data.get("body"), "Message", max_len=2000)

    eta = None
    if data.get("reminder_time"):
        try:
            eta = datetime.fromisoformat(str(data["reminder_time"]).replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError("reminder_time must be an ISO 8601 date-time")
        if eta.tzinfo is None:
            eta = eta.replace(tzinfo=timezone.utc)

    try:
        from tasks import send_reminder

        count = 0
        for user in User.query.filter(User.id.in_([i for i in ids if isinstance(i, int)])).all():
            if user.is_admin or not user.active:
                continue
            send_reminder.apply_async(args=[user.email, subject, body], eta=eta)
            count += 1
    except Exception as exc:  # noqa: BLE001
        from flask import current_app

        current_app.logger.warning("Could not queue reminders: %s", exc)
        return error("Background job service (Redis/Celery) is unavailable", 503)
    return jsonify({"scheduled": True, "count": count})
