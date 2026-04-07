.PHONY: dev lint test alembic-revision alembic-upgrade seed worker beat

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check app tests

test:
	pytest

alembic-revision:
	alembic revision --autogenerate -m "$(m)"

alembic-upgrade:
	alembic upgrade head

seed:
	python -m app.scripts.seed_phase1

worker:
	celery -A app.workers.celery_app.celery_app worker -l info -Q critical,notifications_high,notifications_bulk,integrations,analytics,maintenance

beat:
	celery -A app.workers.celery_app.celery_app beat -l info
