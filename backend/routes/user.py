import os

from celery.result import AsyncResult
from flask import Blueprint, current_app, jsonify, request, send_file
from flask_security import current_user
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import ParkingLot, ParkingSpot, Reservation, utcnow
from utils import error, json_body, number, text, token_roles

user_bp = Blueprint("user_api", __name__, url_prefix="/api/user")
user_only = token_roles("user")


# ------------------------------------------------------------------ profile
@user_bp.get("/profile")
@user_only
def get_profile():
    return jsonify(current_user.to_dict())


@user_bp.put("/profile")
@user_only
def update_profile():
    data = json_body()
    u = current_user
    u.full_name = text(data.get("full_name", u.full_name), "Full name", min_len=2, max_len=150, required=True)
    u.phone = text(data.get("phone", u.phone), "Phone", max_len=15)
    u.vehicle_number = text(data.get("vehicle_number", u.vehicle_number), "Vehicle number", max_len=20).upper()
    db.session.commit()
    return jsonify({"success": True, "user": u.to_dict()})


@user_bp.delete("/account")
@user_only
def delete_account():
    if Reservation.query.filter_by(user_id=current_user.id, is_active=True).first():
        return error("Release your active reservation before deleting your account", 400)
    current_user._get_current_object().anonymise()  # soft delete: history is kept
    db.session.commit()
    return jsonify({"success": True, "message": "Account deleted"})


# -------------------------------------------------------------- parking lots
@user_bp.get("/parking_lots")
@user_only
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


# -------------------------------------------------------------- reservations
@user_bp.post("/reserve")
@user_only
def reserve_spot():
    data = json_body()
    lot_id = number(data.get("lot_id"), "lot_id", cast=int, required=True)
    lot = db.session.get(ParkingLot, lot_id)
    if not lot or lot.deleted_at is not None:
        return error("Parking lot not found", 404)
    if Reservation.query.filter_by(user_id=current_user.id, is_active=True).first():
        return error("You already have an active reservation", 400)

    # Claim a free spot with an atomic UPDATE ... WHERE status='A': two users can
    # never get the same spot. We walk through *every* free spot (not just the
    # first few), so a lot is only reported full when it really has no free spot.
    claimed = None
    free_ids = [i for (i,) in db.session.query(ParkingSpot.id)
                .filter_by(lot_id=lot.id, status="A").order_by(ParkingSpot.id).all()]
    for spot_id in free_ids:
        res = db.session.execute(
            update(ParkingSpot)
            .where(ParkingSpot.id == spot_id, ParkingSpot.status == "A")
            .values(status="O")
        )
        if res.rowcount == 1:
            claimed = db.session.get(ParkingSpot, spot_id)
            break
    if not claimed:
        db.session.rollback()
        return error("No available spots in this lot", 400)

    reservation = Reservation(
        spot_id=claimed.id,
        user_id=current_user.id,
        parking_cost=lot.price_per_hour,
        parking_timestamp=utcnow(),
        is_active=True,
    )
    db.session.add(reservation)
    try:
        db.session.commit()
    except IntegrityError:
        # A parallel request from the same user won the race. The unique index
        # rejected this one, and the rollback also frees the spot we just claimed.
        db.session.rollback()
        return error("You already have an active reservation", 400)
    return jsonify({"success": True, "reservation": reservation.to_dict()}), 201


@user_bp.post("/release")
@user_only
def release_spot():
    data = json_body()
    reservation_id = number(data.get("reservation_id"), "reservation_id", cast=int, required=True)
    reservation = db.session.get(Reservation, reservation_id)
    if not reservation or reservation.user_id != current_user.id:
        return error("Reservation not found", 404)
    if not reservation.is_active:
        return error("Reservation already released", 400)

    reservation.leaving_timestamp = utcnow()
    reservation.is_active = False
    reservation.parking_spot.status = "A"
    db.session.commit()
    return jsonify({"success": True, "reservation": reservation.to_dict()})


@user_bp.get("/my_reservations")
@user_only
def my_reservations():
    rows = (
        Reservation.query.filter_by(user_id=current_user.id)
        .order_by(Reservation.created_at.desc(), Reservation.id.desc())
        .all()
    )
    return jsonify([r.to_dict() for r in rows])


@user_bp.delete("/reservations/<int:reservation_id>")
@user_only
def delete_reservation(reservation_id):
    """Remove a finished reservation from the user's history."""
    r = db.session.get(Reservation, reservation_id)
    if not r or r.user_id != current_user.id:
        return error("Reservation not found", 404)
    if r.is_active:
        return error("Release the spot before deleting this record", 400)
    db.session.delete(r)
    db.session.commit()
    return jsonify({"success": True})


@user_bp.get("/stats")
@user_only
def user_stats():
    done = Reservation.query.filter_by(user_id=current_user.id, is_active=False).all()
    all_count = Reservation.query.filter_by(user_id=current_user.id).count()
    return jsonify(
        {
            "total_reservations": all_count,
            "total_hours": round(sum(r.duration_hours for r in done), 2),
            "total_spent": round(sum(r.total_cost for r in done), 2),
        }
    )


# --------------------------------------------------- CSV export (Celery job)
@user_bp.post("/export")
@user_only
def start_export():
    try:
        from tasks import export_reservations_csv

        task = export_reservations_csv.delay(current_user.id)
    except Exception as exc:  # noqa: BLE001  (Redis down, etc.)
        current_app.logger.warning("Could not queue export: %s", exc)
        return error("Background job service (Redis/Celery) is unavailable", 503)
    return jsonify({"message": "Export started", "task_id": task.id}), 202


@user_bp.get("/export/<task_id>")
@user_only
def export_status(task_id):
    try:
        result = AsyncResult(task_id, app=current_app.extensions["celery"])
        state = result.state
        payload = result.result if state == "SUCCESS" else None
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("Could not read export result: %s", exc)
        return error("Background job service (Redis/Celery) is unavailable", 503)

    if state == "SUCCESS":
        if not isinstance(payload, dict) or payload.get("user_id") != current_user.id:
            return error("Export not found", 404)
        path = os.path.join(current_app.config["EXPORT_DIR"], os.path.basename(payload["file"]))
        if not os.path.exists(path):
            return error("Export file no longer exists", 404)
        return send_file(path, mimetype="text/csv", as_attachment=True, download_name="reservations.csv")
    if state in ("FAILURE", "REVOKED"):
        return error("Export failed, please try again", 500)
    return jsonify({"status": state}), 202
