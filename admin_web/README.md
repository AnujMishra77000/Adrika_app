# ADR Admin Dashboard (Next.js)

Phase 2 admin console for student-side operational control.

## Setup

1. Copy env:
   - `cp .env.local.example .env.local`
2. Install:
   - `npm install`
3. Run dev server:
   - `npm run dev`

## Key routes

- `/login`
- `/admin`
- `/admin/students`
- `/admin/notices`
- `/admin/homework`
- `/admin/attendance`
- `/admin/assessments`
- `/admin/results`
- `/admin/doubts`
- `/admin/content`
- `/admin/notifications`
- `/admin/audit-logs`

## API dependency

The dashboard expects backend APIs under:
- `NEXT_PUBLIC_API_BASE_URL` (default example `http://localhost:8000`)
- FastAPI routes under `/api/v1/auth/*` and `/api/v1/admin/*`
