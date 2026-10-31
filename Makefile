.PHONY: up down discover test migrate reset
up:
	docker compose up --build -d
down:
	docker compose down
discover:
	docker compose exec api python scripts/seed.py
test:
	python -m pytest -q
migrate:
	alembic upgrade head
reset:
	sh scripts/reset.sh
