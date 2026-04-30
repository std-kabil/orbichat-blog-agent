You are working inside the Python agent repository:

/home/kabil/Work/orbichat-blog-agent/agent

There is also a symlink to the existing OrbiChat frontend repository at:

/home/kabil/Work/orbichat-blog-agent/orbichat-web

Do not modify the frontend repo unless a specific task explicitly requires it. For this PRD, focus mainly on building the Python blog/growth agent backend.

# PRD: OrbiChat Blog/Growth Agent

## 1. Product overview

We are building an internal AI-powered blog/growth agent for OrbiChat.ai.

OrbiChat.ai is a multi-model AI chat platform. The marketing goal is to grow organic traffic by publishing high-quality, trend-aware blog content around AI models, AI chat tools, AI productivity, AI for students, AI for developers, and model comparisons.

This should not be a generic AI blog generator. It should work like an internal editorial growth system:

- Discover relevant trends.
- Find credible sources.
- Score topic opportunities.
- Generate SEO angles.
- Create outlines.
- Write high-quality article drafts.
- Extract factual claims.
- Verify claims against sources.
- Polish the article for the OrbiChat brand.
- Generate social posts.
- Run final publish judgment.
- Save drafts for human review.
- Track cost, sources, and agent runs.

The first production version should generate drafts, not auto-publish by default.

AUTO_PUBLISH must default to false.

---

## 2. Core goals

Build a production-ready Python backend service that can:

1. Run a daily trend discovery workflow.
2. Run a weekly blog generation workflow.
3. Store topics, sources, drafts, fact checks, social posts, model calls, and run logs in PostgreSQL.
4. Expose FastAPI endpoints for triggering and inspecting agent workflows.
5. Use Celery + Redis for long-running jobs.
6. Use OpenRouter for all model calls, including Qwen, Kimi, GPT, and Claude-family models.
7. Use a single model API key: `OPENROUTER_API_KEY`.
8. Use Tavily, Exa, and Brave Search for research/source verification.
9. Track estimated token/model/search costs.
10. Keep all outputs reviewable and auditable.
11. Prepare integration points for the OrbiChat frontend/admin dashboard and Payload CMS later.

---

## 3. Non-goals for this phase

Do not build the full frontend/admin UI yet.

Do not modify the OrbiChat frontend repo unless explicitly asked.

Do not implement direct publishing to Payload CMS yet unless the endpoint/client abstraction is simple and safe.

Do not auto-publish posts.

Do not build a complex vector database or semantic memory system yet.

Do not add LangChain, CrewAI, AutoGen, or unnecessary agent frameworks.

Do not overengineer. Use simple, explicit Python modules and functions.

---

## 4. Required tech stack

Use exactly this stack.

### Backend language

Python 3.11+

### API

FastAPI

### Worker system

Celery

### Queue/cache

Redis

### Database

PostgreSQL

### ORM/migrations

SQLAlchemy 2.x  
Alembic

### Data validation

Pydantic v2  
pydantic-settings

### HTTP client

httpx

### Retries

tenacity

### Logging

loguru

### LLM providers

OpenRouter using an OpenAI-compatible API client for all model calls

### Search/research providers

Tavily  
Exa  
Brave Search API  
Google Trends/manual feed support can be represented as a placeholder module for now.

### Monitoring

Sentry SDK

### Testing

pytest

### Code quality

ruff  
mypy

### Containerization

Docker  
docker-compose

---

## 5. Model routing

Implement the code so model names are configurable through environment variables, but use the following defaults in settings.

### Trend discovery

Tools:

- Tavily
- Brave
- Google Trends/manual feeds placeholder

No LLM required by default except for normalization/deduplication if needed.

### Source finding

Tools:

- Tavily
- Exa

### Topic scoring

Model:

- Qwen3.6 Plus through OpenRouter

Purpose:

- Score each topic from 0 to 100.
- Judge OrbiChat relevance.
- Judge SEO opportunity.
- Judge conversion potential.
- Return structured JSON.

### SEO angles

Model:

- Kimi K2.6 through OpenRouter

Purpose:

- Generate SEO angle options.
- Determine search intent.
- Suggest article positioning.
- Suggest CTA angle for OrbiChat.

### Outline

Model:

- Kimi K2.6 through OpenRouter

Purpose:

- Generate article outline.
- Include headings, sections, FAQ, internal links, CTA placement.

### Article writing

Model:

- Claude Sonnet 4.6 through OpenRouter

Purpose:

- Write the main long-form article draft.
- Style should be natural, useful, and non-generic.
- Avoid AI-slop.
- Avoid fake claims.
- Include source-aware factual statements.

### Claim extraction

Model:

- Kimi K2.6 through OpenRouter

Purpose:

- Extract factual claims from the article.
- Classify claims by risk level.
- Identify which claims need source verification.

### Source verification

Tools:

- Tavily
- Exa
- Brave
- deterministic rules

Purpose:

- Verify extracted claims against sources.
- Mark each claim as supported, unsupported, unclear, or opinion.

### Risky claim review

Model:

- GPT-5.4 mini or GPT-5.4 through OpenRouter

Purpose:

- Review only risky/unsupported/unclear claims.
- Decide whether to remove, rewrite, or cite.

### Brand polish

Model:

- Claude Sonnet 4.6 through OpenRouter

Purpose:

- Improve article clarity, tone, flow, and brand fit.
- Keep content factual.
- Do not add new factual claims without sources.

### Social posts

Model:

- Claude Haiku 4.5 through OpenRouter

Purpose:

- Generate social posts for X/Twitter, LinkedIn, Reddit-style post, and short announcement.

### Publish judgment

Model:

- GPT-5.4 through OpenRouter plus deterministic rules

Purpose:

- Final pass/fail decision.
- Return JSON with score, risks, and required fixes.

---

## 6. Environment variables

Use pydantic-settings to load configuration.

Required environment variables:

```env
APP_ENV=development
APP_NAME=orbichat-blog-agent
API_HOST=0.0.0.0
API_PORT=8000

DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/orbichat_blog_agent
REDIS_URL=redis://redis:6379/0

OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

TAVILY_API_KEY=
EXA_API_KEY=
BRAVE_API_KEY=

PAYLOAD_API_URL=
PAYLOAD_API_KEY=

CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_BUCKET=
CLOUDFLARE_R2_ENDPOINT=

PLAUSIBLE_API_KEY=
PLAUSIBLE_SITE_ID=

SENTRY_DSN=

AUTO_PUBLISH=false
MIN_PUBLISH_SCORE=85

AGENT_DAILY_BUDGET_USD=2.00
AGENT_MONTHLY_BUDGET_USD=50.00

TOPIC_SCORING_MODEL=qwen/qwen3.6-plus
SEO_ANGLES_MODEL=moonshotai/kimi-k2.6
OUTLINE_MODEL=moonshotai/kimi-k2.6
CLAIM_EXTRACTION_MODEL=moonshotai/kimi-k2.6
RISKY_CLAIM_REVIEW_MODEL=openai/gpt-5.4-mini
PUBLISH_JUDGMENT_MODEL=openai/gpt-5.4

ARTICLE_WRITING_MODEL=anthropic/claude-sonnet-4.6
BRAND_POLISH_MODEL=anthropic/claude-sonnet-4.6
SOCIAL_POSTS_MODEL=anthropic/claude-haiku-4.5
````

Do not hardcode API keys. All model calls must use `OPENROUTER_API_KEY`; do not add provider-specific model API keys such as `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. Provider prefixes in model IDs, such as `anthropic/...`, are OpenRouter model identifiers and do not require separate provider API keys.

---

## 7. Repository structure

The project should use this structure:

```txt
agent/
  app/
    __init__.py
    main.py
    config.py
    db.py
    models.py
    dependencies.py
    errors.py

  api/
    __init__.py
    routes_health.py
    routes_runs.py
    routes_topics.py
    routes_drafts.py
    routes_costs.py

  agents/
    __init__.py
    trend_discovery.py
    source_finder.py
    topic_scorer.py
    seo_angles.py
    outline_generator.py
    article_writer.py
    claim_extractor.py
    source_verifier.py
    risky_claim_reviewer.py
    brand_polisher.py
    social_generator.py
    publish_judge.py
    orchestrator.py

  jobs/
    __init__.py
    celery_app.py
    daily_trend_scan.py
    weekly_blog_generation.py
    analytics_sync.py

  services/
    __init__.py
    llm_router.py
    openrouter_client.py
    tavily_client.py
    exa_client.py
    brave_client.py
    payload_client.py
    r2_client.py
    plausible_client.py
    cost_tracker.py
    deduplication.py
    slugger.py

  schemas/
    __init__.py
    common.py
    topic.py
    source.py
    draft.py
    fact_check.py
    qa.py
    social.py
    run.py
    cost.py

  prompts/
    topic_scoring.md
    seo_angles.md
    outline.md
    article_writer.md
    claim_extraction.md
    risky_claim_review.md
    brand_polish.md
    social_posts.md
    publish_judgment.md

  tests/
    __init__.py
    test_health.py
    test_schemas.py
    test_publish_rules.py

  alembic/
    versions/

  outputs/
    .gitkeep

  Dockerfile
  docker-compose.yml
  pyproject.toml
  alembic.ini
  .env.example
  README.md
  .gitignore
```

If some folders already exist, update them safely.

---

## 8. Database schema

Create SQLAlchemy models and Alembic migrations for the following tables.

Use UUID primary keys where practical.

### agent_runs

Tracks each workflow execution.

Fields:

```txt
id UUID primary key
run_type string // daily_scan, weekly_blog_generation, manual_draft, verify_draft, analytics_sync
status string // queued, running, completed, failed, cancelled
started_at datetime nullable
finished_at datetime nullable
total_cost_usd numeric default 0
total_input_tokens integer default 0
total_output_tokens integer default 0
error_message text nullable
metadata_json jsonb default {}
created_at datetime
updated_at datetime
```

### trend_candidates

Raw trend ideas from sources.

```txt
id UUID primary key
run_id UUID FK agent_runs.id
title text
query text nullable
source string // tavily, exa, brave, google_trends, manual
url text nullable
snippet text nullable
detected_at datetime
raw_score numeric nullable
metadata_json jsonb default {}
created_at datetime
```

### topics

Processed/scored topics.

```txt
id UUID primary key
run_id UUID FK agent_runs.id nullable
title text
target_keyword text nullable
search_intent text nullable
summary text nullable

trend_score integer
orbichat_relevance_score integer
seo_score integer
conversion_score integer
total_score integer

recommended boolean default false
reasoning text nullable
cta_angle text nullable
status string // candidate, approved, rejected, drafted, published

created_at datetime
updated_at datetime
```

### sources

Research sources connected to topics/drafts.

```txt
id UUID primary key
topic_id UUID FK topics.id nullable
draft_id UUID FK blog_drafts.id nullable

url text
title text nullable
publisher text nullable
author text nullable
published_at datetime nullable
extracted_text text nullable
snippet text nullable
credibility_score integer nullable
source_type string nullable // news, docs, blog, forum, official, unknown
used_in_article boolean default false
metadata_json jsonb default {}

created_at datetime
updated_at datetime
```

### blog_drafts

Generated article drafts.

```txt
id UUID primary key
topic_id UUID FK topics.id

title text
slug text unique
meta_title text nullable
meta_description text nullable
target_keyword text nullable
markdown_content text
outline_json jsonb default {}
seo_json jsonb default {}

status string // draft, needs_review, approved, rejected, published
version integer default 1

publish_score integer nullable
publish_ready boolean default false
payload_post_id text nullable

created_at datetime
updated_at datetime
```

### fact_checks

Claim verification results.

```txt
id UUID primary key
draft_id UUID FK blog_drafts.id

claim text
claim_type string nullable // pricing, benchmark, news, product_feature, general, opinion
verdict string // supported, unsupported, unclear, opinion
severity string // low, medium, high
explanation text nullable
source_urls_json jsonb default []
recommended_action string nullable // keep, cite, rewrite, remove
created_at datetime
```

### social_posts

Generated social content.

```txt
id UUID primary key
draft_id UUID FK blog_drafts.id

platform string // x, linkedin, reddit, short_announcement
content text
status string // draft, approved, rejected, posted
metadata_json jsonb default {}

created_at datetime
updated_at datetime
```

### llm_calls

Tracks every model call.

```txt
id UUID primary key
run_id UUID FK agent_runs.id nullable
draft_id UUID FK blog_drafts.id nullable
topic_id UUID FK topics.id nullable

task_name string
provider string // openrouter
model string

input_tokens integer default 0
output_tokens integer default 0
estimated_cost_usd numeric default 0
latency_ms integer nullable
success boolean default true
error text nullable

created_at datetime
```

### search_calls

Tracks external search API usage.

```txt
id UUID primary key
run_id UUID FK agent_runs.id nullable
topic_id UUID FK topics.id nullable
draft_id UUID FK blog_drafts.id nullable

provider string // tavily, exa, brave
query text
result_count integer default 0
estimated_cost_usd numeric default 0
latency_ms integer nullable
success boolean default true
error text nullable

created_at datetime
```

### analytics_snapshots

Stores imported analytics later.

```txt
id UUID primary key
draft_id UUID FK blog_drafts.id nullable
payload_post_id text nullable
date date

page_views integer default 0
unique_visitors integer default 0
cta_clicks integer default 0
signups integer default 0
search_impressions integer nullable
search_clicks integer nullable
avg_position numeric nullable

created_at datetime
```

---

## 9. API endpoints

Implement clean FastAPI routes.

### Health

```txt
GET /
GET /health
```

`GET /health` should return:

```json
{
  "status": "ok",
  "service": "orbichat-blog-agent"
}
```

### Runs

```txt
POST /runs/daily-scan
POST /runs/weekly-blog-generation
GET /runs
GET /runs/{run_id}
```

POST endpoints should enqueue Celery jobs and return run/job info.

### Topics

```txt
GET /topics
GET /topics/{topic_id}
POST /topics/{topic_id}/approve
POST /topics/{topic_id}/reject
POST /topics/{topic_id}/generate-draft
```

### Drafts

```txt
GET /drafts
GET /drafts/{draft_id}
POST /drafts/{draft_id}/verify
POST /drafts/{draft_id}/polish
POST /drafts/{draft_id}/publish-judgment
POST /drafts/{draft_id}/approve
POST /drafts/{draft_id}/reject
```

Do not implement real publishing yet. If adding a route, make it safe:

```txt
POST /drafts/{draft_id}/send-to-payload
```

This should only be a placeholder unless Payload API details are available.

### Costs

```txt
GET /costs/summary
GET /costs/runs/{run_id}
```

Return total estimated cost, tokens, model usage.

---

## 10. Workflow details

### Daily trend scan workflow

Implemented in:

```txt
agents/orchestrator.py
jobs/daily_trend_scan.py
```

Steps:

1. Create `agent_runs` row with status `running`.
2. Build seed queries for OrbiChat-relevant topics.
3. Search Tavily.
4. Search Brave.
5. Optionally use manual Google Trends placeholder source.
6. Normalize results into `TrendCandidate` schema.
7. Deduplicate similar candidates.
8. Save candidates to database.
9. Group candidates into possible topics.
10. Score topics using Qwen3.6 Plus.
11. Save topics to database.
12. Mark run completed.
13. Track LLM/search call costs.

Seed topic areas:

```txt
AI chat apps
ChatGPT alternatives
Claude vs GPT
Gemini vs Claude
Grok vs ChatGPT
best AI model for coding
best AI model for students
best AI model for writing
AI productivity tools
OpenRouter models
new AI model releases
AI coding assistants
AI search tools
multi-model AI chat
```

The output should be a list of scored topics.

### Weekly blog generation workflow

Implemented in:

```txt
agents/orchestrator.py
jobs/weekly_blog_generation.py
```

Steps:

1. Create `agent_runs` row.
2. Select top approved topic if available.
3. If no approved topic exists, use highest-scoring recommended topic.
4. Find sources with Tavily and Exa.
5. Save sources.
6. Generate SEO angles with Kimi.
7. Generate outline with Kimi.
8. Write article with Claude Sonnet through OpenRouter.
9. Extract factual claims with Kimi.
10. Verify claims through Tavily/Exa/Brave and deterministic rules.
11. Review risky claims with GPT-5.4 mini/GPT-5.4.
12. Brand polish with Claude Sonnet through OpenRouter.
13. Generate social posts with Claude Haiku through OpenRouter.
14. Run deterministic publish checks.
15. Run GPT-5.4 publish judgment.
16. Save draft, fact checks, social posts.
17. Mark topic as `drafted`.
18. Mark run completed.

The workflow should be robust to partial failure. If article writing succeeds but social post generation fails, keep the draft and mark the run as completed_with_warnings or failed with useful error metadata.

Use `status` values consistently.

---

## 11. Structured schemas

Use Pydantic schemas for all LLM outputs.

### Topic score output

```json
{
  "title": "string",
  "target_keyword": "string",
  "search_intent": "informational | commercial | navigational | comparison | tutorial",
  "trend_score": 0,
  "orbichat_relevance_score": 0,
  "seo_score": 0,
  "conversion_score": 0,
  "total_score": 0,
  "recommended": true,
  "reasoning": "string",
  "cta_angle": "string"
}
```

### SEO angles output

```json
{
  "primary_angle": "string",
  "alternative_angles": ["string"],
  "target_audience": "string",
  "search_intent": "string",
  "primary_keyword": "string",
  "secondary_keywords": ["string"],
  "recommended_title": "string",
  "meta_description": "string",
  "cta_strategy": "string"
}
```

### Outline output

```json
{
  "title": "string",
  "slug": "string",
  "meta_title": "string",
  "meta_description": "string",
  "sections": [
    {
      "heading": "string",
      "goal": "string",
      "key_points": ["string"]
    }
  ],
  "faq": [
    {
      "question": "string",
      "answer_goal": "string"
    }
  ],
  "internal_links": ["string"],
  "cta_placements": ["string"]
}
```

### Blog draft output

The article writer can return Markdown plus metadata.

```json
{
  "title": "string",
  "slug": "string",
  "meta_title": "string",
  "meta_description": "string",
  "markdown_content": "string",
  "notes": "string"
}
```

### Claim extraction output

```json
{
  "claims": [
    {
      "claim": "string",
      "claim_type": "pricing | benchmark | news | product_feature | general | opinion",
      "risk_level": "low | medium | high",
      "needs_verification": true
    }
  ]
}
```

### Source verification output

```json
{
  "claim": "string",
  "verdict": "supported | unsupported | unclear | opinion",
  "severity": "low | medium | high",
  "source_urls": ["string"],
  "explanation": "string",
  "recommended_action": "keep | cite | rewrite | remove"
}
```

### Publish judgment output

```json
{
  "publish_ready": false,
  "score": 0,
  "risk_level": "low | medium | high",
  "required_fixes": ["string"],
  "reasoning": "string"
}
```

---

## 12. Deterministic publish rules

Before calling the final publish judgment model, run deterministic checks.

Block publish if:

1. Article has fewer than 900 words.
2. Article has no sources for factual/news/model claims.
3. There are any high-severity unsupported claims.
4. There are more than 2 medium-severity unclear claims.
5. OrbiChat CTA appears more than 3 times.
6. Title is empty or too clickbait-like.
7. Meta description is missing.
8. Slug is missing.
9. Article contains placeholder text.
10. Article says “as an AI language model.”
11. Article uses fake citations.
12. Article includes direct pricing/benchmark claims without source verification.
13. AUTO_PUBLISH is false.

Even if the model says publish_ready true, deterministic rules win.

---

## 13. Prompt requirements

Create initial prompts in the `prompts/` directory.

Prompts should be strict and structured.

General rules for all prompts:

* Return valid JSON when a schema is expected.
* Do not include markdown fences around JSON.
* Do not invent sources.
* Do not invent pricing or benchmark data.
* Be honest about uncertainty.
* Optimize for useful, trustworthy content.
* Avoid generic AI-slop.
* Keep OrbiChat mention natural and not spammy.

### Brand writing direction

OrbiChat blog style:

* Clear.
* Useful.
* Practical.
* Honest.
* Not overhyped.
* Not generic.
* Avoid “unlock the power of AI” style.
* Prefer concrete examples.
* Prefer comparison tables where useful.
* Soft CTA: “try multiple models in one place.”
* Do not attack competitors unfairly.

---

## 14. LLM client design

Implement:

```txt
services/llm_router.py
services/openrouter_client.py
```

`llm_router.py` should expose high-level functions:

```python
async def call_openrouter_json(...)
async def call_openrouter_text(...)
```

Each model call should:

1. Measure latency.
2. Estimate or record tokens if provider returns usage.
3. Estimate cost if pricing table is configured.
4. Save an `llm_calls` row.
5. Retry transient errors using tenacity.
6. Fail clearly with useful error messages.

Do not scatter raw provider calls across agent files. Use centralized clients.

---

## 15. Search client design

Implement:

```txt
services/tavily_client.py
services/exa_client.py
services/brave_client.py
```

Each search call should:

1. Accept a query.
2. Return normalized search results.
3. Track latency.
4. Save `search_calls`.
5. Retry transient errors.
6. Never crash the whole run if one provider fails; return partial results with warnings.

Normalized search result schema:

```json
{
  "title": "string",
  "url": "string",
  "snippet": "string",
  "published_at": "datetime or null",
  "source_provider": "tavily | exa | brave",
  "raw": {}
}
```

---

## 16. Cost tracking

Implement `services/cost_tracker.py`.

Track:

* LLM input tokens.
* LLM output tokens.
* Estimated LLM cost.
* Search API call cost if possible.
* Cost per run.
* Cost per draft.
* Cost per model.
* Daily/monthly budget checks.

If daily budget is exceeded, block non-critical workflows and return a useful error.

Budget behavior:

```txt
Daily trend scan can run if under daily budget.
Weekly generation can run if under monthly budget.
Manual calls should warn if budget exceeded.
```

Do not rely on exact pricing being perfect. Use estimated cost fields.

---

## 17. FastAPI behavior

FastAPI app should:

* Include route modules.
* Configure CORS for local frontend development.
* Initialize Sentry if SENTRY_DSN exists.
* Return structured errors.
* Expose OpenAPI docs.
* Provide health check.

CORS local origins:

```txt
http://localhost:3000
http://127.0.0.1:3000
```

---

## 18. Celery behavior

Celery should define tasks:

```txt
daily_trend_scan
weekly_blog_generation
analytics_sync
generate_draft_for_topic
verify_draft
polish_draft
publish_judgment
```

Use Redis broker/result backend.

Celery beat schedule:

```txt
daily_trend_scan: once per day
weekly_blog_generation: once per week
analytics_sync: once per day
```

Use safe placeholder schedules. Make them configurable later.

---

## 19. Docker requirements

`docker-compose.yml` should run:

```txt
agent-api
agent-worker
agent-scheduler
redis
postgres
```

The API command:

```txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The worker command:

```txt
celery -A jobs.celery_app worker --loglevel=info
```

The scheduler command:

```txt
celery -A jobs.celery_app beat --loglevel=info
```

Postgres should expose local port 5432 or a safe alternative.

Redis should expose local port 6379.

Use `.env` file support.

---

## 20. Payload CMS integration

Do not fully implement publishing unless enough information is available.

Create `services/payload_client.py` with placeholder methods:

```python
class PayloadClient:
    async def create_draft_post(...)
    async def update_draft_post(...)
    async def get_post(...)
```

For now, it can raise `NotImplementedError` or return a clear placeholder response.

The expected future flow:

```txt
Agent creates draft
↓
Payload draft post created
↓
Human reviews
↓
Human publishes in Payload/admin
↓
Next.js blog displays it
```

---

## 21. Frontend integration contract

The frontend will later call this API.

Keep the API clean and typed so we can generate a TypeScript client from:

```txt
/openapi.json
```

Do not create frontend code now.

The frontend will eventually need:

* List agent runs.
* List topics.
* Approve/reject topics.
* Generate draft for topic.
* View draft.
* View fact-check report.
* Trigger polish.
* Trigger publish judgment.
* View cost summary.

---

## 22. Testing requirements

Add tests for:

1. Health endpoint.
2. Pydantic schemas.
3. Deterministic publish rules.
4. Cost tracker simple calculation.
5. Slug generation.
6. Deduplication logic.

Use pytest.

Tests should not require real API keys.

Mock external services.

---

## 23. Implementation phases

Implement this project in phases.

### Phase 1: Infrastructure foundation

* Settings/config.
* FastAPI routes.
* SQLAlchemy models.
* Alembic migration.
* Docker Compose.
* Celery setup.
* Basic tests.
* Health endpoint.

### Phase 2: Data schemas and database persistence

* Pydantic schemas.
* CRUD helpers or repository functions.
* Agent run tracking.
* Topic/source/draft persistence.
* LLM/search call tracking.

### Phase 3: External service clients

* OpenRouter client.
* Tavily client.
* Exa client.
* Brave client.
* Cost tracking wrappers.

### Phase 4: Daily trend scan

* Seed queries.
* Search providers.
* Deduplication.
* Topic scoring.
* Save results.
* API endpoint to trigger.

### Phase 5: Weekly blog generation

* Source finding.
* SEO angles.
* Outline.
* Article writing.
* Claim extraction.
* Source verification.
* Risk review.
* Brand polish.
* Social posts.
* Publish judgment.
* Save draft.

### Phase 6: Safety, quality, and monitoring

* Deterministic publish rules.
* Budget checks.
* Sentry integration.
* Better logs.
* More tests.

---

## 24. Acceptance criteria

The project is considered successful for this phase if:

1. `docker compose up` starts API, worker, scheduler, Redis, and Postgres.
2. `GET /health` returns OK.
3. Alembic migration creates required tables.
4. `POST /runs/daily-scan` enqueues or runs the daily scan workflow.
5. Daily scan stores trend candidates and scored topics.
6. `GET /topics` returns stored topics.
7. `POST /topics/{topic_id}/generate-draft` can create a draft workflow.
8. Draft generation stores a blog draft and related metadata.
9. Fact-check records are stored for claims.
10. LLM and search calls are logged.
11. Cost summary endpoint works.
12. Tests pass.
13. No real API call is required for tests.
14. AUTO_PUBLISH defaults to false.
15. No code modifies the symlinked frontend repo.

---

## 25. Development rules

Follow these rules strictly:

1. Keep implementation simple and explicit.
2. Do not add unnecessary frameworks.
3. Do not hardcode secrets.
4. Do not auto-publish.
5. Do not edit `../orbichat-web` unless explicitly instructed.
6. Use type hints.
7. Use Pydantic schemas for agent outputs.
8. Use centralized clients for LLM/search calls.
9. Make external API calls easy to mock.
10. Keep prompts in the `prompts/` directory.
11. Track every model/search call.
12. Prefer readable code over clever abstractions.
13. Commit logical changes if git is initialized.

---

## 26. First task to start now

Start with Phase 1 only.

Implement:

1. Clean FastAPI app structure.
2. Config loading with pydantic-settings.
3. SQLAlchemy database connection.
4. SQLAlchemy models for the required tables.
5. Alembic setup and initial migration.
6. Celery app and placeholder tasks.
7. Docker Compose working with API, worker, scheduler, Redis, and Postgres.
8. Basic routes:

   * GET /
   * GET /health
   * POST /runs/daily-scan
   * POST /runs/weekly-blog-generation
   * GET /runs
9. Basic tests.
10. Update README with setup commands.

Do not implement the full AI workflows yet in this first task.

After Phase 1, print:

* What files were created/changed.
* How to run locally.
* How to run with Docker Compose.
* How to run tests.
* Any assumptions or TODOs.
