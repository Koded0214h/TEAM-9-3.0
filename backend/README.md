# Repelect backend

## Local setup

```bash
cp .env.example .env
docker compose up -d db
uv sync --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The API documentation is available at `http://localhost:8000/docs`. Health endpoints are:

- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

Run checks with:

```bash
uv run ruff check .
uv run pytest
```
