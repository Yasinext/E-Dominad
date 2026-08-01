.PHONY: test lint format typecheck check db-start db-stop migrate smoke

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src

check: lint typecheck test

db-start:
	/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D /opt/homebrew/var/postgresql@16 -l /tmp/domainbot-postgres.log start

db-stop:
	/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D /opt/homebrew/var/postgresql@16 stop

migrate:
	alembic -c alembic.ini upgrade head

smoke:
	python scripts/local_smoke.py
