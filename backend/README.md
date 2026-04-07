# ADR Platform Backend

FastAPI modular monolith for coaching institute automation.

## Local run (without Docker)

1. Copy env (already SQLite-ready):
   - `cp .env.example .env`
2. Install:
   - `pip install -e .[dev]`
3. Apply DB migrations:
   - `alembic upgrade head`
4. Seed sample data:
   - `python -m app.scripts.seed_phase1`
5. Start API:
   - `uvicorn app.main:app --reload --port 8000`

## Local services notes

- DB: uses SQLite by default (`sqlite+aiosqlite:///./adr_dev.db`) for local development.
- Cache: if Redis is not running, API automatically falls back to in-memory cache.
- Redis is still recommended for realistic performance testing.

## Workers

- Celery worker:
  - `celery -A app.workers.celery_app.celery_app worker -l info`
- Celery beat:
  - `celery -A app.workers.celery_app.celery_app beat -l info`

## Default seeded users

- Student: `student@adr.local` / `Student@123`
- Teacher: `teacher@adr.local` / `Teacher@123`
- Admin: `admin@adr.local` / `Admin@123`
- Parent: `parent@adr.local` / `Parent@123`

## Health

- `GET /health/live`
- `GET /health/ready`
