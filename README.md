# Vehicle Parking Management System

![CI](https://github.com/YashRaj-IITM/Vehicle-Parking/actions/workflows/ci.yml/badge.svg)

A full-stack parking management system. **Users** browse parking lots, reserve the first free spot, release it when they leave (the cost is calculated from the time parked) and review their history. The **admin** creates and manages parking lots and spots, manages users and sees live statistics and revenue.

## Features

**User** - register / login, edit profile (phone, vehicle number), search parking lots, reserve a spot (one active reservation at a time), release a spot and see the cost, view and remove history records, personal summary (bookings, hours, spend), export history as CSV (background job), delete own account.

**Admin** - create / edit / delete parking lots (spots are created and removed automatically), view every spot and who occupies it, delete a free spot, search / blacklist / delete users, view all reservations, dashboard statistics with charts (occupancy per lot, revenue, per-user usage), schedule reminder e-mails to users.

**Background jobs (Celery + Redis)**

| Job | Trigger | What it does |
|---|---|---|
| `export_reservations_csv` | User clicks *Export history* | Builds a CSV, e-mails it and makes it downloadable |
| `send_reminder` | Admin schedules reminders (optionally at a chosen time) | E-mails the selected users |
| `daily_parking_reminders` | Celery beat, daily 18:00 | Reminds users who have not booked a spot today |
| `monthly_activity_report` | Celery beat, 1st of the month 09:00 | E-mails every user an HTML report of the previous month (bookings, hours, spend, favourite lot) |

## Requirements coverage

| Requirement | Where it is implemented |
|---|---|
| User authentication (login + registration) | `backend/routes/auth.py`; Flask-Security-Too hashes passwords and manages users and roles; Vue pages `Login`, `Register` |
| Token-based authentication | Login returns a Flask-Security access token. User and admin endpoints require a valid access token and the appropriate role. Authentication endpoints that require login validate the token without requiring a specific user role. The Axios interceptor in frontend/src/api.js sends the Authentication-Token header. No session cookies are used.|
| RESTful API | Resource-based endpoints under `/api` with proper verbs and status codes (see *API documentation*) |
| CRUD operations | Parking lots (create, read, update, delete), spots (read, delete), reservations (create, read, update on release, delete), users (read, update profile / status, delete) |
| Automated tests and CI | `backend/tests/` (pytest) and `.github/workflows/ci.yml` |
| Backend jobs (optional) | Celery + Redis: CSV export, reminders, daily reminder, monthly report |
| Stack | Flask, SQLAlchemy, Flask-Security-Too, Vue 3, Axios, Celery, Redis |

## Tech stack

- **Backend:** Flask, Flask-SQLAlchemy (SQLAlchemy 2), Flask-Security-Too, Flask-Mail, Flask-CORS
- **Frontend:** Vue 3, Vue Router, Axios, Chart.js, Bootstrap 5
- **Jobs:** Celery, Redis, MailHog (local e-mail testing)
- **Database:** SQLite (any SQLAlchemy URL works via `DATABASE_URL`)

## Project structure

```
Vehicle-Parking/
├── backend/
│   ├── app.py              # app factory (Security, CORS, Celery, blueprints)
│   ├── config.py           # settings, read from environment / .env
│   ├── models.py           # SQLAlchemy models + Flask-Security datastore
│   ├── seed.py             # roles + default admin
│   ├── utils.py            # validation helpers, token_roles decorator
│   ├── routes/             # auth.py, admin.py, user.py
│   ├── tasks.py            # Celery jobs
│   ├── celery_worker.py    # Celery entry point
│   ├── tests/              # pytest suite (56 tests, no Redis needed)
│   ├── requirements.txt
│   └── requirements-dev.txt  # + pytest
├── frontend/               # Vue 3 app (src/api.js, router, views)
└── .github/workflows/ci.yml  # runs backend tests + frontend lint/build on every push
```

## Installation

Run the backend and frontend in separate terminals. Redis, the Celery worker and Celery beat each need their own terminal when you use background jobs.

### Prerequisites
Python 3.10+, Node.js 18+, and (only for background jobs) Redis. MailHog is optional.

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then set SECRET_KEY and SECURITY_PASSWORD_SALT (see below)
python app.py                     # http://127.0.0.1:5000
```
Tables, roles and the default admin are created automatically on first start.

**Secrets are mandatory.** The backend refuses to start (with a clear error) while `SECRET_KEY` or `SECURITY_PASSWORD_SALT` is missing, shorter than 16 characters, or still a placeholder such as `change-me...`. Generate a value for each and paste them into `backend/.env`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Admin account:** created on first start from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `backend/.env`. Set your own password there before the first run; the app logs a warning while a placeholder is in use. Never commit your `.env` file.

### 2. Frontend
```bash
cd frontend
npm install
npm run serve                     # http://localhost:8080
```
The dev server proxies `/api` to Flask, so no extra configuration is needed.

### 3. Background jobs (optional)
```bash
redis-server                                                      # terminal 1
cd backend && celery -A celery_worker.celery_app worker --loglevel=info --pool=solo   # terminal 2
cd backend && celery -A celery_worker.celery_app beat -l info     # terminal 3 (scheduled jobs)
```
For e-mail testing run MailHog (`mailhog`) and open http://localhost:8025. Without Redis the app still works; export and reminder actions report that the job service is unavailable. For this project's local Mac development setup, use `--pool=solo` for the Celery worker. Keep Redis running while using background jobs.

### 4. Run the tests
```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q
```
The suite (56 tests) covers authentication and roles, lot CRUD, reservation rules (including no double booking and price frozen at booking time), user management and soft deletion, the Celery tasks (run eagerly, no Redis needed) and the fail-fast secret check. Every test gets a fresh in-memory database.

**Continuous integration:** `.github/workflows/ci.yml` runs the backend tests on Python 3.10 and 3.12 and the frontend lint and build on every push and pull request. The badge at the top of this README displays the current GitHub Actions workflow status.

## Authentication

Login returns an access token issued by Flask-Security. Send it on every protected request:

```
Authentication-Token: <token>
```

Tokens expire after 8 hours and are invalidated on logout or when the account is blacklisted. Missing / invalid token -> `401`; wrong role -> `403`.

```bash
curl -X POST http://127.0.0.1:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<ADMIN_EMAIL>","password":"<ADMIN_PASSWORD>"}'

curl http://127.0.0.1:5000/api/admin/stats -H "Authentication-Token: <token>"
```

## API documentation

All API endpoints are under `/api`. Most endpoints accept and return JSON; the reservation export endpoint returns a downloadable CSV file. Error responses are returned as JSON, with the fields depending on the type of error.

### Auth
| Method | Endpoint | Auth | Body / notes |
|---|---|---|---|
| POST | `/auth/register` | - | `email`, `password` (min 8), `full_name`, `phone?`, `vehicle_number?` |
| POST | `/auth/login` | - | `email`, `password` -> `{token, user}` |
| POST | `/auth/logout` | token | invalidates the user's tokens |
| GET | `/auth/me` | token | current user |
| GET | `/health` | - | health check |

### User (role `user`)
| Method | Endpoint | Description |
|---|---|---|
| GET / PUT | `/user/profile` | read / update `full_name`, `phone`, `vehicle_number` |
| DELETE | `/user/account` | delete own account (not allowed while a spot is reserved); the account is anonymised and its reservation history is kept |
| GET | `/user/parking_lots?q=` | lots with `available_spots` / `occupied_spots`; search by name, address or PIN |
| POST | `/user/reserve` | `{lot_id}` - claims the first free spot atomically (400 if the lot is full or the user already has an active reservation) |
| POST | `/user/release` | `{reservation_id}` - frees the spot and returns duration and cost |
| GET | `/user/my_reservations` | own reservations, newest first |
| DELETE | `/user/reservations/<id>` | remove a finished reservation from history |
| GET | `/user/stats` | `total_reservations`, `total_hours`, `total_spent` |
| POST | `/user/export` | start CSV export job -> `202 {task_id}` |
| GET | `/user/export/<task_id>` | `202` while running, `200` + CSV file when done |

### Admin (role `admin`)
| Method | Endpoint | Description |
|---|---|---|
| GET / POST | `/admin/parking_lots` | list (`?q=`) / create: `prime_location_name`, `price_per_hour`, `address`, `pin_code`, `maximum_number_of_spots` |
| GET / PUT / DELETE | `/admin/parking_lots/<id>` | read / update (spots are added or removed to match the new maximum; removal is refused if an occupied spot, or a spot with reservation history, would go) / delete (refused while a spot is occupied; soft delete, history is kept) |
| GET | `/admin/parking_lots/<id>/spots` | every spot with its current occupant |
| DELETE | `/admin/spots/<id>` | delete a free spot (refused if it has reservation history) |
| GET | `/admin/users?q=` | list / search users |
| PUT | `/admin/users/<id>/status` | `{"action": "blacklist" \| "activate"}` |
| DELETE | `/admin/users/<id>` | delete a user: closes and bills any open booking, frees the spot, anonymises the account and keeps the history |
| GET | `/admin/reservations?active=true` | all reservations |
| GET | `/admin/stats` | totals, per-lot occupancy, per-user usage, revenue |
| POST | `/admin/schedule_bulk_reminders` | `{user_ids, subject, body, reminder_time?}` - queues reminder e-mails |

## Demo walkthrough (about 3 minutes)

1. Start the backend and frontend (see *Installation*) and open http://localhost:8080.
2. Log in as the admin (the `ADMIN_EMAIL` / `ADMIN_PASSWORD` from your `.env`).
3. Create a parking lot (for example 5 spots at ₹40/hour). Click *View Spots* to see them.
4. In a private window register a user, log in and reserve a spot. The admin's spot view now shows who is parked there.
5. Release the spot as the user and check the cost; open *Stats* as the admin to see occupancy and revenue.
6. As the admin open *Users* to blacklist a user (their token stops working immediately).
7. With Redis, the worker and MailHog running, click *Export history (CSV)* as a user to receive the file by e-mail.

## Data model

`User` (+ `Role`, Flask-Security) 1-N `Reservation`; `ParkingLot` 1-N `ParkingSpot`; `ParkingSpot` 1-N `Reservation`. A reservation stores the lot's price per hour at booking time, so later price changes do not alter past bills. **History is preserved.** Deleting a lot is a soft delete (`ParkingLot.deleted_at`): the lot vanishes from every list and can no longer be booked, but its spots and reservations stay. Deleting a user anonymises the account (`User.deleted_at`; name, phone, vehicle number and e-mail are erased, login and old tokens are blocked) and keeps the reservations, so past bills and revenue totals do not change. A spot that has reservation history cannot be deleted. The one-active-reservation-per-user rule is enforced by a unique index, which is created with the tables, so after upgrading an existing database (this version also adds the `deleted_at` columns) delete `backend/vehicle_parking.db` and let it be re-created.

## Troubleshooting

| Problem | Fix |
|---|---|
| `RuntimeError: SECRET_KEY is not set` / `is a placeholder or too short` | Create `backend/.env` from `.env.example` and put real random values in `SECRET_KEY` and `SECURITY_PASSWORD_SALT` (command in *Installation*) |
| `ModuleNotFoundError: flask_security` | Activate the virtual environment and run `pip install -r requirements.txt` inside `backend/` |
| Frontend shows network errors | Make sure the backend is running on port 5000; the dev server proxies `/api` to it (`frontend/vue.config.js`) |
| Export / reminders say the job service is unavailable | Start Redis and the Celery worker (see *Background jobs*); the rest of the app works without them |
| Login returns 401 after a long time | Tokens expire after 8 hours or after logout; log in again |
| Want a fresh database | Stop the server, delete `backend/vehicle_parking.db`, start again (the admin account is re-created) |
| `ModuleNotFoundError: No module named 'pkg_resources'` | `setuptools<81` is pinned because `passlib` needs it; reinstall the requirements |

## Security notes

- Passwords are hashed by Flask-Security; the API is stateless and token based (no cookies, so no CSRF surface).
- Secrets come from `.env` (not committed). The app refuses to start without strong `SECRET_KEY` and `SECURITY_PASSWORD_SALT` values, so there is no predictable default signing key. Change the admin password before any real deployment; the app logs a warning while the default is in use.
- All input is validated server-side; role checks use `@auth_required("token")` + `@roles_required(...)`.
- Reservations are race-safe: spots arith an atomic `UPDATE ... WHERE status='A'` (two users can never receive the same spot, and every free spot is tried before a lot is reported full), and a partial unique index on active reservations guarantees one active reservation per user at the database level, even when requests arrive simultaneously.
