SHELL := /usr/bin/bash
venv:
	uv venv .venv

test:
	uv run pytest -vv --show-capture=all backend/test_main.py 

install:
	uv sync --locked

run:
	PYTHONPATH=backend/ uv run uvicorn backend.main:app --reload

ruff:
	uv add --dev ruff
		
check: ruff
	uv run ruff check --fix

format: ruff
	uv run ruff format

migrate:
	uv run alembic upgrade head

migrate_current:
	uv run alembic current

