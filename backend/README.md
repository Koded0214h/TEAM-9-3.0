# TallyTrail backend

```bash
cp .env.example .env
docker compose up -d
uv sync --dev
uv run alembic upgrade head
uv run python -m app.scripts.bootstrap_admin
uv run uvicorn app.main:app --reload
```

Checks:

```bash
uv run ruff check .
uv run pytest
```
