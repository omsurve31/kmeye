.PHONY: lint lint-backend lint-frontend test test-backend test-frontend check format run

# Run these from an activated backend virtualenv (see README); CI installs into the system Python.

lint: lint-backend lint-frontend

lint-backend:
	cd backend && python -m ruff check . && python -m ruff format --check . && python -m mypy

lint-frontend:
	cd frontend && npm run lint && npm run format:check && npm run typecheck

test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest --cov-report=xml
	cd backend && python -m coverage report --include="*/forecast_selection.py,*/metrics.py" --fail-under=100

test-frontend:
	cd frontend && npm test

check: lint test

format:
	cd backend && python -m ruff check --fix . && python -m ruff format .
	cd frontend && npm run format

run:
	docker compose up --build
