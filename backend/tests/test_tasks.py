from datetime import timedelta

import tasks
from extensions import db
from models import ParkingLot, ParkingSpot, Reservation, User, utcnow


def _seed_history(app, api):
    api.register("t@example.com")
    with app.app_context():
        u = User.query.filter_by(email="t@example.com").first()
        lot = ParkingLot(prime_location_name="L", price_per_hour=10, address="addr", pin_code="123", maximum_number_of_spots=1)
        db.session.add(lot)
        db.session.flush()
        spot = ParkingSpot(lot_id=lot.id, spot_number="P1")
        db.session.add(spot)
        db.session.flush()
        last_month = utcnow().replace(day=1) - timedelta(days=3)
        db.session.add(Reservation(spot_id=spot.id, user_id=u.id, parking_timestamp=last_month,
                                   leaving_timestamp=last_month + timedelta(hours=2), parking_cost=10,
                                   is_active=False, created_at=last_month))
        db.session.commit()
        return u.id


def test_csv_export_task(app, api, tmp_path):
    app.config["EXPORT_DIR"] = str(tmp_path)
    uid = _seed_history(app, api)
    with app.app_context():
        out = tasks.export_reservations_csv.run(uid)
    assert out["rows"] == 1
    assert "Reservation ID" in (tmp_path / out["file"]).read_text()


def test_daily_reminder_task(app, api):
    _seed_history(app, api)
    with app.app_context():
        assert tasks.daily_parking_reminders.run()["reminders_sent"] == 1   # nobody booked today


def test_monthly_report_task(app, api, tmp_path):
    app.config["EXPORT_DIR"] = str(tmp_path)
    _seed_history(app, api)
    with app.app_context():
        assert tasks.monthly_activity_report.run()["reports_sent"] == 1
    assert list(tmp_path.glob("report_*.html"))
