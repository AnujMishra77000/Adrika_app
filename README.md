# Adr App Platform

Production-grade coaching institute automation platform.

## Repositories in this monorepo

- `backend/`: FastAPI modular monolith (Phase 1 in progress)
- `mobile_app/`: Flutter app scaffold (student + teacher)
- `admin_web/`: Admin dashboard scaffold
- `docs/`: Architecture and operational docs

## Current status

Phase 1 backend foundation started with:
- auth + RBAC primitives
- student-focused modules (notices, homework, attendance read, tests, results/progress, doubts, notifications)
- PostgreSQL + Redis + Celery integrations
- Alembic migrations + seed script
- pytest baseline
