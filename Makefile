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

.PHONY: frontend-dev frontend-check local-stack
frontend-dev:
	cd frontend && npm run dev
frontend-check:
	cd frontend && npm run typecheck && npm run lint && npm test && npm run build
local-stack:
	python scripts/dev_stack.py
