import secrets
from datetime import datetime, timezone

from flask_security import RoleMixin, SQLAlchemyUserDatastore, UserMixin, hash_password

from extensions import db


def utcnow():
    """Naive UTC datetime (all datetimes in the DB are UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt):
    """ISO string with a trailing Z so browsers parse it as UTC."""
    return dt.isoformat() + "Z" if dt else None


roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
)


class Role(db.Model, RoleMixin):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.UnicodeText)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(15))
    vehicle_number = db.Column(db.String(20))
    # Flask-Security: `active` False means blacklisted / cannot log in
    active = db.Column(db.Boolean, default=True, nullable=False)
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    deleted_at = db.Column(db.DateTime)  # set when the account is deleted (soft delete)

    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )
    # No delete cascade: reservation history must survive the user.
    reservations = db.relationship("Reservation", backref="user", lazy=True)

    @property
    def is_admin(self):
        return self.has_role("admin")

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def anonymise(self):
        """Soft-delete the account.

        The row (and every reservation that points at it) is kept, so billing history and
        revenue figures stay correct, but personal data is erased and the account can no
        longer be used: login is blocked, old tokens are invalidated and the e-mail address
        becomes free for a new registration.
        """
        self.email = f"deleted-{self.id}@deleted.invalid"
        self.full_name = "Deleted user"
        self.phone = None
        self.vehicle_number = None
        self.password = hash_password(secrets.token_urlsafe(32))  # unusable random password
        self.active = False
        self.deleted_at = utcnow()
        user_datastore.set_uniquifier(self)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "vehicle_number": self.vehicle_number,
            "is_admin": self.is_admin,
            "active": self.active,
            "role": "admin" if self.is_admin else "user",
            "created_at": iso(self.created_at),
        }


class ParkingLot(db.Model):
    __tablename__ = "parking_lots"
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(200), nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(500), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    maximum_number_of_spots = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    deleted_at = db.Column(db.DateTime)  # set when the lot is deleted (soft delete)

    parking_spots = db.relationship(
        "ParkingSpot", backref="parking_lot", cascade="all, delete-orphan", lazy=True
    )

    @classmethod
    def live(cls):
        """Query over lots that have not been deleted."""
        return cls.query.filter(cls.deleted_at.is_(None))

    @property
    def available_spots(self):
        return ParkingSpot.query.filter_by(lot_id=self.id, status="A").count()

    @property
    def occupied_spots(self):
        return ParkingSpot.query.filter_by(lot_id=self.id, status="O").count()

    def to_dict(self):
        return {
            "id": self.id,
            "prime_location_name": self.prime_location_name,
            "price_per_hour": self.price_per_hour,
            "address": self.address,
            "pin_code": self.pin_code,
            "maximum_number_of_spots": self.maximum_number_of_spots,
            "available_spots": self.available_spots,
            "occupied_spots": self.occupied_spots,
        }


class ParkingSpot(db.Model):
    __tablename__ = "parking_spots"
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey("parking_lots.id"), nullable=False)
    spot_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(1), default="A", nullable=False)  # A=Available, O=Occupied
    created_at = db.Column(db.DateTime, default=utcnow)

    # No delete cascade: a spot that has reservation history can never be removed.
    reservations = db.relationship("Reservation", backref="parking_spot", lazy=True)

    @property
    def is_available(self):
        return self.status == "A"

    @property
    def is_occupied(self):
        return self.status == "O"


class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey("parking_spots.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    parking_timestamp = db.Column(db.DateTime, default=utcnow)
    leaving_timestamp = db.Column(db.DateTime)
    parking_cost = db.Column(db.Float, default=0.0)  # price/hour frozen at booking time
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    # Database-level guarantee: a user can never hold two active reservations,
    # even when several requests arrive at the same instant.
    __table_args__ = (
        db.Index(
            "uq_one_active_reservation_per_user",
            "user_id",
            unique=True,
            sqlite_where=db.text("is_active = 1"),
            postgresql_where=db.text("is_active"),
        ),
    )

    @property
    def duration_hours(self):
        if self.leaving_timestamp:
            return round((self.leaving_timestamp - self.parking_timestamp).total_seconds() / 3600, 2)
        return 0

    @property
    def total_cost(self):
        return round((self.parking_cost or 0) * self.duration_hours, 2)

    def to_dict(self):
        spot = self.parking_spot
        lot = spot.parking_lot if spot else None
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else None,
            "spot_id": self.spot_id,
            "spot_number": spot.spot_number if spot else None,
            "lot_id": spot.lot_id if spot else None,
            "lot_name": lot.prime_location_name if lot else None,
            "parking_timestamp": iso(self.parking_timestamp),
            "leaving_timestamp": iso(self.leaving_timestamp),
            "is_active": self.is_active,
            "parking_cost_per_hour": self.parking_cost,
            "duration_hours": self.duration_hours,
            "total_cost": self.total_cost,
        }


user_datastore = SQLAlchemyUserDatastore(db, User, Role)
