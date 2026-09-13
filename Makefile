PY ?= .venv/bin/python

.PHONY: setup test demo lint

setup:
	uv venv -p 3.12 .venv
	uv pip install -p .venv -e ".[dev]"
	docker compose up -d db
	$(PY) -c "from aiforge_core.db import connect, run_migrations; run_migrations(connect(), 'migrations')"

test:
	$(PY) -m pytest -q

demo:
	$(PY) -m uvicorn app.main:production_app --factory --host 0.0.0.0 --port 8000

lint:
	$(PY) -m ruff check .
