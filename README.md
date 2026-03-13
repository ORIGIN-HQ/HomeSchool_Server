# Homeschool Connect - Backend API

This is the backend server for **Homeschool Connect**, an app we were building to help homeschooling parents and tutors in the same area find each other. The core idea was simple: put people on a map, let them see who is nearby, and give them a way to reach out. No directories, no paid listings, just a location-aware community layer.

This repo represents the API built during the MVP phase. We were trying to validate whether homeschooling families would actually use a proximity-based discovery tool before investing further into mobile development.

---

## What the app was trying to do

Homeschooling can be isolating. Parents want to co-op with other families, find subject-specific tutors nearby, and build a community with people who share their educational approach. The app put a pin on a map for every registered parent or tutor, let users see who was within their area, and enabled contact via WhatsApp when both parties were open to it.

The user flow went like this:

1. Sign in via Google (migrated to Clerk during the project)
2. Choose a role, parent or tutor
3. Set your location and a visibility radius
4. See nearby pins on a map
5. Tap a pin to see a preview
6. View a full profile
7. Contact via WhatsApp if the person has enabled it

Everything in this backend is oriented around making that flow work reliably and respecting user privacy throughout.

---

## Tech stack

- **FastAPI** for the web framework
- **PostgreSQL** with the **PostGIS** extension for geospatial queries
- **SQLAlchemy** and **GeoAlchemy2** for the ORM and spatial types
- **Alembic** for database migrations
- **Clerk** for authentication (JWT verification via JWKS)
- **Docker** for running PostgreSQL locally

---

## Project structure

```
HomeSchool_Server/
├── app/
│   ├── api/
│   │   ├── auth.py          # /auth/me and /auth/set-role
│   │   ├── profiles.py      # /parents and /tutors onboarding
│   │   ├── map.py           # /map/pins and /map/preview/{id}
│   │   └── contact.py       # /contact/whatsapp/{id} and /contact/log
│   ├── core/
│   │   ├── dependencies.py  # JWT verification and user sync
│   │   ├── security.py      # Token utilities
│   │   └── logging.py       # Logging setup
│   ├── db/
│   │   ├── database.py      # SQLAlchemy engine and session
│   │   └── models.py        # User, Parent, Tutor, ContactLog models
│   ├── schemas/             # Pydantic request/response models
│   ├── services/
│   │   └── clerk_auth.py    # Clerk JWKS fetching and token verification
│   ├── config.py            # Pydantic settings from .env
│   └── main.py              # App entry point, routers, middleware
├── alembic/                 # Migration scripts
├── tests/                   # pytest test suites per feature
├── docker-compose.yml       # PostgreSQL + PostGIS container
├── requirements.txt
└── .env.example
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Docker (for the database)
- A Clerk account for authentication

### 1. Clone and install

```bash
git clone https://github.com/your-username/homeschool-server.git
cd homeschool-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values. The critical ones are:

```
DATABASE_URL=postgresql://homeschool_user:homeschool_pass@localhost:5432/homeschool_db
SECRET_KEY=your-secret-key
CLERK_JWT_ISSUER=https://your-app.clerk.accounts.dev
CLERK_SECRET_KEY=sk_test_...
```

### 3. Start PostgreSQL with PostGIS

```bash
docker-compose up -d
```

This spins up a `postgis/postgis:15-3.3` container with the PostGIS extension pre-enabled.

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs are at `/docs`.

---

## API overview

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/me` | Get current user profile from Clerk JWT |
| POST | `/auth/set-role` | Set user role (parent or tutor, one time only) |

Roles are permanent once set. The frontend uses `/auth/me` to determine whether to show onboarding or go straight to the map.

### Profiles and onboarding

| Method | Path | Description |
|--------|------|-------------|
| POST | `/parents` | Create parent profile with location |
| POST | `/tutors` | Create tutor profile with location |
| GET | `/profiles/{user_id}` | Full profile view for another user |

Location is stored as a PostGIS `POINT` geometry in WGS84 (SRID 4326). The visibility radius defaults to 5km but users can set between 500m and 50km.

### Map

| Method | Path | Description |
|--------|------|-------------|
| GET | `/map/pins` | Get all visible pins within a viewport bounding box |
| GET | `/map/preview/{user_id}` | Lightweight preview when a pin is tapped |

The `/map/pins` endpoint accepts `ne_lat`, `ne_lng`, `sw_lat`, `sw_lng` as viewport bounds and runs a PostGIS `ST_Intersects` against a `ST_MakeEnvelope`. Optional filters include type (parent/tutor), curriculum, subject, and max distance. Results are capped at 500 pins. Only first names are returned in pin responses for privacy.

### Contact

| Method | Path | Description |
|--------|------|-------------|
| GET | `/contact/whatsapp/{user_id}` | Generate a `wa.me` deep link with a prefilled message |
| POST | `/contact/log` | Log a contact attempt for analytics |

WhatsApp contact is gated behind a per-user toggle. If `whatsapp_enabled` is false, the endpoint returns 404. Phone numbers are cleaned and standardised to international format before being embedded in the `wa.me` link.

---

## Database models

**users** holds the shared data for all account types including the PostGIS location column and visibility radius. There is a GIST spatial index on the location field.

**parents** and **tutors** are separate tables linked to users via `user_id`. JSON string columns hold lists like `children_ages`, `subjects`, and `certifications` rather than separate junction tables, which was fine for the MVP.

**contact_logs** records every WhatsApp contact attempt for analytics.

---

## Running tests

Tests use a separate test database and real PostGIS queries rather than mocks.

```bash
pytest tests/ -v
```

Make sure `TEST_DATABASE_URL` is set in your environment or `conftest.py`:

```
postgresql://homeschool_user:homeschool_pass@localhost:5432/homeschool_test
```

Test files are organised by feature, mirroring the GitHub issue structure used during development:

- `test_location_setup.py` - profile creation and geo index verification
- `test_map_pins.py` - viewport queries, filters, distance
- `test_pin_preview.py` - preview endpoint privacy and structure
- `test_full_profile.py` - full profile data, WhatsApp privacy
- `test_whatsapp_contact.py` - link generation, phone formatting, contact logging

---

## Privacy decisions

A few intentional choices worth noting:

**Pins on the public map show first name only.** The full name only becomes visible after a user taps through to the preview or full profile. This gives people a soft degree of anonymity when browsing.

**WhatsApp numbers are never returned unless the user explicitly enables it.** Even if a number exists in the database, the contact endpoint returns 404 if `whatsapp_enabled` is false. The full profile endpoint does the same.

**Users set their own visibility radius.** Shrinking the radius down to 500m is enough to make precise location hard to determine. The location itself is the pin centroid, not a jittered version, but the radius setting gives users meaningful control.

**Exact coordinates are only visible in the full profile view**, not in the map pin list. The assumption is that by reaching the full profile, there has been enough intent from the viewer to justify showing the location precisely.

---

## Authentication flow

The app moved from Google OAuth to Clerk partway through the build. The `google_id` column in the users table now stores the Clerk user ID (`user_xxx...`). The authentication service fetches the Clerk JWKS endpoint on first request, caches the keys, and verifies incoming JWTs against them. If a Clerk user does not yet have a local record, they are auto-created from the Clerk API response on first login.

---

## Known limitations and shortcuts taken for MVP

- JSON strings for array fields like `subjects` and `children_ages` instead of proper array columns or relational tables
- Auto-verification of tutors at signup with no actual credential checking
- No rate limiting on contact endpoints
- The `visibility_radius` column is stored but the map pins endpoint does not currently filter against individual user radii, only the viewport bounding box
- CORS is set to allow all origins in development mode

These were conscious tradeoffs to ship faster and see whether the core concept had legs before cleaning things up.

---

## Contributing

This was a solo MVP but if you want to pick it up or extend it, the general conventions are:

- One router file per domain area under `app/api/`
- Pydantic schemas live in `app/schemas/` and mirror the API file names
- Database models are all in `app/db/models.py`
- New features should have a corresponding test file in `tests/`
- Migration files are generated with `alembic revision --autogenerate -m "description"`

Please do not commit `.env` files or any credentials. The `.gitignore` already excludes these but it bears repeating.

---

## License

MIT
