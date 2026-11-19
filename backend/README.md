# TallyTrail backend

```bash
cp .env.example .env
docker compose up -d
uv sync --dev
uv run alembic upgrade head
uv run python -m app.scripts.bootstrap_admin
uv run uvicorn app.main:app --reload
```

Run background reconciliation, IReV adapter, and export jobs:

```bash
uv run celery -A app.core.celery.celery_app worker --loglevel=INFO
```

Cloudinary objects use authenticated delivery and expiring signed access URLs. Automated IReV
retrieval remains disabled until an approved public endpoint contract is configured; manual public
document import remains available and is always labelled `public_irev`.

Checks:

```bash
uv run ruff check .
uv run pytest
```
