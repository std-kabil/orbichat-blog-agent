# OrbiChat Blog Agent

Python/FastAPI backend foundation for the OrbiChat Blog/Growth Agent.

Phase 1 includes the API structure, settings, SQLAlchemy models, Alembic migration, Celery placeholders, Docker Compose, and basic tests. It does not implement real AI workflows or external provider calls yet.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
cp .env.example .env
```

Update `.env` for your local PostgreSQL and Redis instances if needed.

Model calls are configured through OpenRouter only. Set `OPENROUTER_API_KEY`; do not add separate Anthropic or OpenAI API keys for individual models.

## Database

Run migrations from this directory:

```bash
alembic upgrade head
```

## API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Celery

Worker:

```bash
celery -A jobs.celery_app worker --loglevel=info
```

Scheduler:

```bash
celery -A jobs.celery_app beat --loglevel=info
```

The Phase 1 Celery tasks are placeholders and do not call OpenRouter, Tavily, Exa, Brave, Payload, R2, or Plausible.

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Apply migrations inside the API container when the database is ready:

```bash
docker compose run --rm agent-api alembic upgrade head
```

## Quality Checks

```bash
python -m pytest
python -m ruff check .
python -m mypy .
```

## Phase 1 Endpoints

- `GET /`
- `GET /health`
- `POST /runs/daily-scan`
- `POST /runs/weekly-blog-generation`
- `GET /runs`

`AUTO_PUBLISH` defaults to `false`. Publishing, provider clients, prompt files, real workflows, and frontend integration are intentionally left for later phases.
