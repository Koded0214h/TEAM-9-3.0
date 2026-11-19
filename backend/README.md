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

## Production checklist

- Set `ENVIRONMENT=production` and `DEBUG=false`.
- Generate a unique high-entropy `AUTH_SECRET_KEY`; never reuse the development value.
- Use a TLS-enabled managed PostgreSQL/PostGIS database and least-privilege credentials.
- Restrict `FRONTEND_ORIGINS` to deployed frontend origins.
- Put the API behind HTTPS and a trusted reverse proxy.
- Replace the in-process rate limiter with Redis or gateway-level distributed limits when running multiple workers.
- Move large export artifacts to private object storage with short-lived signed URLs.
- Configure encrypted backups and test restoration.
- Send structured logs to protected centralized storage and set retention rules for audit events and exports.
- Restrict the Geoapify key by allowed APIs and rotate it if exposed.
