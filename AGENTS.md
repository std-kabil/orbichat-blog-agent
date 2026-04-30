# AGENTS.md — OrbiChat Blog Agent Engineering Rules

This repository contains the backend for the OrbiChat Blog/Growth Agent.

The goal is to build a production-quality, maintainable, type-safe Python service for AI-assisted trend discovery, source research, blog draft generation, claim verification, brand polish, and workflow monitoring.

This file defines strict rules for any coding agent working in this repository.

---

## 1. Core Engineering Principles

Write code as if it will be maintained by a real engineering team.

Prioritize:

- Correctness
- Readability
- Type safety
- Explicit data flow
- Testability
- Observability
- Security
- Small, composable modules
- Clear error handling
- Production deployment readiness

Avoid:

- AI-generated-looking code
- Clever abstractions without need
- Huge files
- Unclear naming
- Hidden side effects
- Silent failures
- Hardcoded secrets
- Mocked “fake success” in production paths
- Frameworks that add complexity without clear value

If a feature is not needed yet, do not build it.

---

## 2. Project Scope

This project is the Python backend for the OrbiChat Blog/Growth Agent.

It should handle:

- Trend discovery
- Source finding
- Topic scoring
- SEO angle generation
- Article outlining
- Article draft generation
- Claim extraction
- Source verification
- Risky claim review
- Brand polishing
- Social post generation
- Publish judgment
- Cost tracking
- Run tracking
- Search/LLM call logging

It must not directly publish content automatically unless explicitly enabled and reviewed.

`AUTO_PUBLISH` must default to `false`.

---

## 3. Repository Boundaries

The frontend repository is available through a symlink:

```txt
../orbichat-web
````

Do not edit files inside `../orbichat-web` unless the user explicitly asks for frontend changes.

This repository should remain focused on:

* FastAPI service
* Celery workers
* PostgreSQL persistence
* LLM/search clients
* Agent workflows
* Tests
* Docker deployment

---

## 4. Required Stack

Use the existing stack only.

Backend:

* Python 3.11+
* FastAPI
* Celery
* Redis
* PostgreSQL
* SQLAlchemy 2.x
* Alembic
* Pydantic v2
* pydantic-settings
* httpx
* tenacity
* loguru
* Sentry SDK
* pytest
* ruff
* mypy

LLM/Search:

* OpenRouter through an OpenAI-compatible client for all model calls
* Tavily
* Exa
* Brave Search API

Do not introduce LangChain, CrewAI, AutoGen, LlamaIndex, Django, Flask, or extra frameworks unless explicitly requested.

---

## 5. Code Style

Write simple, boring, readable code.

Use descriptive names.

Good:

```python
async def score_topic_candidate(candidate: TrendCandidate) -> TopicScore:
    ...
```

Bad:

```python
async def do_ai_stuff(x):
    ...
```

Rules:

* Use type hints everywhere.
* Use Pydantic models for external/input/output data shapes.
* Use SQLAlchemy models for persistence.
* Keep functions small.
* Avoid deeply nested logic.
* Avoid global mutable state.
* Prefer explicit dependency injection over hidden imports.
* Do not use broad `except Exception` unless re-raising or logging with context.
* Do not swallow errors silently.
* Do not print in production code; use logging.

---

## 6. Type Safety Rules

All new code must be type-safe.

Required:

* Type annotations for function arguments and return values.
* Pydantic models for structured data.
* Enums or Literal types for fixed status values where appropriate.
* No untyped dictionaries for core domain data.
* No `Any` unless there is a strong reason and a comment explaining why.

Prefer:

```python
class TopicStatus(str, Enum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"
    DRAFTED = "drafted"
    PUBLISHED = "published"
```

Avoid:

```python
status = "some random string"
```

---

## 7. Configuration and Secrets

All configuration must come from environment variables through `app/config.py`.

Never hardcode:

* API keys
* Database URLs
* Redis URLs
* OpenRouter model provider key
* Search provider keys
* Production URLs
* Secrets
* Tokens

`.env` must not be committed.

`.env.example` should contain safe placeholders only.

If a required setting is missing, fail clearly with a helpful error.

---

## 8. Database Rules

Use PostgreSQL as the source of truth.

Use:

* SQLAlchemy 2.x models
* Alembic migrations
* UUID primary keys where practical
* Timestamps on persistent entities
* JSONB for flexible metadata where needed

Do not:

* Store important state only in memory
* Store generated workflow outputs only in local files
* Modify the database schema without an Alembic migration
* Use raw SQL unless there is a clear reason

Every persistent workflow entity should be auditable.

Track:

* Agent runs
* Topics
* Sources
* Drafts
* Fact checks
* Social posts
* LLM calls
* Search calls
* Costs

---

## 9. API Design Rules

FastAPI endpoints should be:

* Small
* Predictable
* Typed
* Easy for the frontend to consume
* OpenAPI-friendly

Use response schemas.

Do not return random unstructured dictionaries from important endpoints.

Good endpoint style:

```python
@router.get("/runs", response_model=list[AgentRunResponse])
async def list_runs(...) -> list[AgentRunResponse]:
    ...
```

Bad endpoint style:

```python
@app.get("/stuff")
def stuff():
    return {"ok": True, "whatever": object()}
```

Endpoints should not perform long-running work directly.

Long-running workflows must be queued through Celery.

---

## 10. Worker and Job Rules

Use Celery for long-running tasks.

The API should enqueue jobs and return quickly.

Celery tasks should:

* Create/update `agent_runs`
* Log progress clearly
* Persist outputs
* Record failures
* Track costs
* Be safe to retry where possible

Never make the frontend wait for a long AI workflow request to complete synchronously.

---

## 11. LLM Client Rules

All LLM calls must go through centralized service clients.

Use:

```txt
services/llm_router.py
services/openrouter_client.py
```

Do not call OpenRouter directly inside agent workflow files; use the centralized OpenRouter client/router. Do not add direct OpenAI or Anthropic model clients or API keys.

Every LLM call must track:

* Provider
* Model
* Task name
* Input tokens if available
* Output tokens if available
* Estimated cost
* Latency
* Success/failure
* Error message if failed

LLM calls must:

* Use timeouts
* Use retries for transient errors
* Return typed results
* Validate JSON outputs with Pydantic when structured output is expected
* Fail clearly when model output is invalid

Never trust model output blindly.

Model provider configuration must stay single-key: `OPENROUTER_API_KEY` is the only model API key. OpenRouter model IDs may use provider prefixes such as `openai/...` or `anthropic/...`, but those prefixes must not introduce direct OpenAI or Anthropic API keys or clients.

---

## 12. Search Client Rules

All external search calls must go through centralized service clients.

Use:

```txt
services/tavily_client.py
services/exa_client.py
services/brave_client.py
```

Every search call must track:

* Provider
* Query
* Result count
* Latency
* Success/failure
* Error message if failed
* Estimated cost if available

Search results should be normalized into a shared schema.

Do not let one failed search provider crash the entire workflow if other providers can still return useful results.

---

## 13. Fact-Checking Rules

Fact-checking must not be model-only.

Required flow:

1. Extract factual claims using a model.
2. Search for sources using Tavily, Exa, and/or Brave.
3. Compare claims against retrieved sources.
4. Mark each claim as:

   * supported
   * unsupported
   * unclear
   * opinion
5. Store fact-check results in the database.
6. Block publishing if serious unsupported claims remain.

Do not allow the final article to include:

* Fake citations
* Unsupported pricing claims
* Unsupported benchmark claims
* Unsupported model release claims
* Fabricated source names
* Invented statistics

---

## 14. Publish Safety Rules

Publishing must be conservative.

Deterministic rules always override model judgment.

Block publish if:

* `AUTO_PUBLISH=false`
* Article has fewer than 900 words
* Meta description is missing
* Slug is missing
* Placeholder text exists
* Unsupported high-severity claims exist
* More than two unclear medium-severity claims exist
* The article includes fake citations
* The article includes direct pricing or benchmark claims without source verification
* The article contains “as an AI language model”
* OrbiChat CTA appears too aggressively

The publish judge model can recommend publishing, but deterministic safety checks decide whether it is allowed.

---

## 15. Brand and Content Quality Rules

OrbiChat content should be:

* Clear
* Practical
* Honest
* Useful
* Specific
* Source-aware
* Easy to read
* Not spammy
* Not overhyped

Avoid generic AI marketing phrases like:

* “Unlock the power of AI”
* “Revolutionize your workflow”
* “In today’s fast-paced digital landscape”
* “Harness the potential”
* “Game-changing solution”
* “Seamless experience” unless specifically justified
* Empty hype without examples

Prefer:

* Concrete comparisons
* Practical examples
* Tables where useful
* Honest pros and cons
* Soft CTA to OrbiChat
* Human-sounding explanations

OrbiChat CTA style:

> Try multiple AI models in one place with OrbiChat.

Do not overuse the CTA.

---

## 16. Error Handling Rules

Errors should be explicit and useful.

When catching errors:

* Log context
* Include provider/model/task when relevant
* Update database run status
* Preserve partial outputs where safe
* Do not hide failures

Bad:

```python
try:
    ...
except Exception:
    pass
```

Good:

```python
try:
    ...
except httpx.TimeoutException as exc:
    logger.warning("Tavily search timed out for query={}", query)
    raise SearchProviderError("Tavily search timed out") from exc
```

---

## 17. Logging Rules

Use structured, useful logs.

Use loguru.

Log:

* Workflow start/end
* Run IDs
* Topic IDs
* Draft IDs
* Provider calls
* Major decisions
* Failures
* Cost summaries

Do not log:

* API keys
* Full secrets
* Private user data
* Huge article bodies unless explicitly needed for debugging

---

## 18. Testing Rules

Add or update tests for every meaningful change.

Required test categories:

* Health endpoint
* Config loading
* Pydantic schemas
* Publish rules
* Cost tracking
* Slug generation
* Deduplication
* API route behavior
* Celery task wiring where practical

Tests must not require real API keys.

External providers must be mocked.

Do not skip tests just because the feature uses AI.

---

## 19. Prompt Rules

Prompts live in:

```txt
prompts/
```

Do not hardcode large prompts inside Python files.

Prompt files should:

* Be clear
* Be task-specific
* Specify output schema
* Forbid fake sources
* Forbid invented claims
* Encourage uncertainty when needed

When expecting JSON:

* Tell the model to return valid JSON only
* Do not accept markdown code fences
* Validate with Pydantic
* Retry or fail if invalid

---

## 20. Cost and Budget Rules

Every LLM/search workflow must be cost-aware.

Track:

* Cost per model call
* Cost per search call
* Cost per run
* Cost per draft
* Daily estimated cost
* Monthly estimated cost

Respect:

* `AGENT_DAILY_BUDGET_USD`
* `AGENT_MONTHLY_BUDGET_USD`

If budget is exceeded, block non-critical generation and return a clear error.

---

## 21. File and Output Rules

Use `outputs/` only for debug/export artifacts.

Do not rely on local files as the source of truth.

Persistent state belongs in PostgreSQL.

Generated outputs should be stored in the database first.

Temporary files should be ignored by git.

---

## 22. Docker and Deployment Rules

The project must run with Docker Compose.

Expected services:

* agent-api
* agent-worker
* agent-scheduler
* redis
* postgres

The API container should run FastAPI.

The worker container should run Celery worker.

The scheduler container should run Celery beat.

Do not assume the developer has global services installed locally.

---

## 23. Security Rules

Treat all external input as untrusted.

Do not:

* Execute arbitrary shell commands from model output
* Trust URLs blindly
* Store secrets in logs
* Return internal stack traces to API users
* Expose admin operations without future auth hooks
* Auto-publish content without explicit permission

When adding frontend integration later, require authentication and role checks.

---

## 24. Dependency Rules

Before adding a dependency, ask:

1. Is it necessary?
2. Is it maintained?
3. Does it reduce complexity?
4. Can the same thing be done clearly without it?

Do not add heavy frameworks for small tasks.

Do not add duplicate libraries that solve the same problem.

---

## 25. Implementation Workflow for Agents

When working on a task:

1. Read the relevant files first.
2. Understand current structure.
3. Make a small plan.
4. Implement minimal production-quality changes.
5. Add or update tests.
6. Run formatting/linting/tests if available.
7. Summarize what changed.
8. Mention any assumptions or follow-up tasks.

Do not rewrite unrelated files.

Do not perform large refactors unless requested.

---

## 26. Code Review Checklist

Before finishing any task, verify:

* Does the code run?
* Are types clear?
* Are schemas validated?
* Are errors handled?
* Are external calls centralized?
* Are secrets avoided?
* Are tests added?
* Is the implementation too clever?
* Is the database migration included if schema changed?
* Is the code readable by a human?
* Does it avoid generic AI-slop patterns?
* Does it preserve project boundaries?

---

## 27. Current Development Priority

Build the system in phases.

Current priority:

1. Infrastructure foundation
2. Database models and migrations
3. API routes
4. Celery jobs
5. External service clients
6. Trend scan workflow
7. Blog generation workflow
8. Fact-check and publish safety
9. Admin/frontend integration later

Do not jump into complex agent behavior before the foundation is solid.

---

## 28. Final Instruction

Be conservative. Be explicit. Be production-minded.

This project should feel like a serious internal growth platform, not a weekend AI script.

When uncertain, choose the simpler, safer, more maintainable solution.
