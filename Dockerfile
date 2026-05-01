FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=30
ENV PIP_RETRIES=2

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY api ./api
COPY agents ./agents
COPY jobs ./jobs
COPY repositories ./repositories
COPY schemas ./schemas
COPY services ./services
COPY prompts ./prompts
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --no-cache-dir .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
