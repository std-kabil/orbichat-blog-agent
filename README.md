# OrbiChat Blog Agent

Python/FastAPI backend foundation for the OrbiChat Blog/Growth Agent.

Current implemented foundations include the API structure, settings, SQLAlchemy models, Alembic migration, typed schemas, persistence helpers, centralized external service clients, and the daily trend scan workflow. Weekly blog generation is still a placeholder.

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

The daily trend scan task calls configured search providers and OpenRouter topic scoring. Weekly blog generation and analytics sync remain placeholders.

Brave Search is optional. If `BRAVE_API_KEY` is set, search workflows should include Brave as an additional provider; if it is empty, workflows should skip Brave without failing.

## External Clients

Model calls must go through `services/llm_router.py` and `services/openrouter_client.py`. OpenRouter is the only model API provider; provider-prefixed model IDs such as `openai/...` or `anthropic/...` are OpenRouter model identifiers and do not require separate provider keys.

Search calls must go through `services/search_router.py` or the provider-specific clients in `services/tavily_client.py`, `services/exa_client.py`, and `services/brave_client.py`. Results are normalized into a shared schema and calls are logged through the database call-log repositories when a DB session is supplied.

## Daily Trend Scan

Start the API, worker, Redis, and PostgreSQL, then trigger a scan:

```bash
curl -X POST http://localhost:8000/runs/daily-scan
curl http://localhost:8000/runs
curl http://localhost:8000/topics
```

The workflow searches the enabled providers, stores raw trend candidates, deduplicates/group candidates, scores topic opportunities through OpenRouter, saves candidate topics, and records run metadata. At least one search provider key and `OPENROUTER_API_KEY` are required for a real run.

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

## Endpoints

- `GET /`
- `GET /health`
- `POST /runs/daily-scan`
- `POST /runs/weekly-blog-generation`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /topics`
- `GET /topics/{topic_id}`
- `POST /topics/{topic_id}/approve`
- `POST /topics/{topic_id}/reject`
- `GET /drafts`
- `GET /drafts/{draft_id}`
- `GET /costs/summary`
- `GET /costs/runs/{run_id}`

`AUTO_PUBLISH` defaults to `false`. Draft generation, publishing, R2/Payload/Plausible integrations, and frontend integration are intentionally left for later phases.
