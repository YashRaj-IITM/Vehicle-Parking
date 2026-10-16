"""Background jobs (Celery + Redis)."""
import csv
import os

from celery import shared_task
from flask import current_app
from flask_mail import Message

from extensions import db, mail
from models import Reservation, User, utcnow


def _send_mail(subject, recipients, body, html=None, attachment=None):
    """Send an email; never raise (MailHog may not be running)."""
    msg = Message(subject=subject, recipients=recipients, body=body, html=html)
    if attachment:
        msg.attach(*attachment)
    try:
        mail.send(msg)
        return True
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("Could not send email to %s: %s", recipients, exc)
        return False


def _export_dir():
    path = current_app.config["EXPORT_DIR"]
    os.makedirs(path, exist_ok=True)
    return path


def _regular_users():
    return [u for u in User.query.filter_by(active=True).all() if not u.is_admin]


# --------------------------------------------------------------------------
# 1. User triggered: export parking history as CSV
# --------------------------------------------------------------------------
@shared_task(name="tasks.export_reservations_csv")
def export_reservations_csv(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    filename = f"reservations_{user_id}_{utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    path = os.path.join(_export_dir(), filename)
    rows = Reservation.query.filter_by(user_id=user_id).order_by(Reservation.id.desc()).all()

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Reservation ID", "Lot", "Spot", "Parked At (UTC)", "Left At (UTC)",
                         "Rate / hour", "Hours", "Total cost", "Status"])
        for r in rows:
            writer.writerow([
                r.id, r.parking_spot.parking_lot.prime_location_name, r.parking_spot.spot_number,
                r.parking_timestamp.strftime("%Y-%m-%d %H:%M"),
                r.leaving_timestamp.strftime("%Y-%m-%d %H:%M") if r.leaving_timestamp else "",
                r.parking_cost, r.duration_hours, r.total_cost, "Active" if r.is_active else "Completed",
            ])

    with open(path, "rb") as fh:
        _send_mail(
            "Your parking history (CSV export)", [user.email],
            f"Hello {user.full_name},\n\nYour parking history export is attached.\n\nClaude Park",
            attachment=(filename, "text/csv", fh.read()),
        )
    return {"user_id": user_id, "file": filename, "rows": len(rows)}


# --------------------------------------------------------------------------
# 2. Admin triggered: custom reminder email (optionally scheduled with an ETA)
# --------------------------------------------------------------------------
@shared_task(name="tasks.send_reminder")
def send_reminder(email, subject, message):
    return _send_mail(subject, [email], message or "You have a reminder from Claude Park.")


# --------------------------------------------------------------------------
# 3. Scheduled (daily 18:00): remind users who have not booked today
# --------------------------------------------------------------------------
@shared_task(name="tasks.daily_parking_reminders")
def daily_parking_reminders():
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sent = 0
    for user in _regular_users():
        booked_today = Reservation.query.filter(
            Reservation.user_id == user.id, Reservation.created_at >= start
        ).first()
        if booked_today:
            continue
        if _send_mail(
            "Parking reminder", [user.email],
            f"Hello {user.full_name},\n\nYou haven't booked a parking spot today. "
            "Log in to Claude Park to reserve one.",
        ):
            sent += 1
    return {"reminders_sent": sent}


# --------------------------------------------------------------------------
# 4. Scheduled (1st of each month, 09:00): monthly activity report per user
# --------------------------------------------------------------------------
@shared_task(name="tasks.monthly_activity_report")
def monthly_activity_report():
    now = utcnow()
    this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # first day of the previous month
    prev_month = this_month.replace(year=this_month.year - 1, month=12) if this_month.month == 1 \
        else this_month.replace(month=this_month.month - 1)

    os.makedirs(_export_dir(), exist_ok=True)
    sent = 0
    for user in _regular_users():
        rows = Reservation.query.filter(
            Reservation.user_id == user.id,
            Reservation.parking_timestamp >= prev_month,
            Reservation.parking_timestamp < this_month,
        ).all()
        if not rows:
            continue
        spent = round(sum(r.total_cost for r in rows), 2)
        hours = round(sum(r.duration_hours for r in rows), 2)
        lots = {}
        for r in rows:
            name = r.parking_spot.parking_lot.prime_location_name
            lots[name] = lots.get(name, 0) + 1
        favourite = max(lots, key=lots.get)
        html = (
            f"<h2>Parking report - {prev_month.strftime('%B %Y')}</h2>"
            f"<p>Hello {user.full_name},</p><ul>"
            f"<li>Bookings: <b>{len(rows)}</b></li><li>Hours parked: <b>{hours}</b></li>"
            f"<li>Total spent: <b>Rs. {spent}</b></li><li>Most used lot: <b>{favourite}</b></li></ul>"
        )
        with open(os.path.join(_export_dir(), f"report_{user.id}_{prev_month:%Y%m}.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
        if _send_mail(f"Your parking report for {prev_month.strftime('%B %Y')}", [user.email],
                      f"Bookings: {len(rows)}, hours: {hours}, spent: Rs. {spent}", html=html):
            sent += 1
    return {"reports_sent": sent}
