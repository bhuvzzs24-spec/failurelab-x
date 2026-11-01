.PHONY: up down discover test migrate reset
up:
	docker compose up --build -d
down:
	docker compose down
discover:
	docker compose exec api python scripts/seed.py
test: test-backend test-frontend
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

.PHONY: start stop restart status logs test-backend test-frontend test-integration
start:
	python scripts/manage.py start
stop:
	python scripts/manage.py stop
restart:
	python scripts/manage.py restart
status:
	python scripts/manage.py status
logs:
	python scripts/manage.py logs
test-backend:
	python -m pytest -q
test-frontend:
	cd frontend && npm run lint && npm run typecheck && npm test && npm run build
test-integration:
	docker compose --profile test run --build --rm tests

.PHONY: local-start local-stop local-status
local-start:
	python scripts/local.py start
local-stop:
	python scripts/local.py stop
local-status:
	python scripts/local.py status

.PHONY: verifier
verifier:
	python scripts/manage.py verifier
