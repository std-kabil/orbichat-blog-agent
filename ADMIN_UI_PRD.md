# OrbiChat Blog Agent Admin UI PRD

## 1. Summary

Build an internal admin UI for the OrbiChat Blog/Growth Agent so an operator can run, inspect, and review the backend workflow without using Swagger or raw API calls.

The UI should be added to the existing `orbichat-web` app in a later implementation step, but this PRD is stored in the backend project because the backend owns the blog agent API contract.

The admin UI is not a public marketing page. It is a dense, utilitarian operations interface for reviewing agent runs, approving topics, generating drafts, inspecting sources and fact checks, checking costs, and making publish-safety decisions.

## 2. Goals

- Let an operator manage the blog agent from a browser.
- Make the daily trend scan and weekly/manual draft workflows visible and controllable.
- Let an operator approve/reject topics before draft generation.
- Let an operator inspect generated drafts, source research, fact checks, social posts, and safety reports.
- Show run status, errors, warnings, metadata, and costs clearly.
- Support safe review-only publishing decisions without Payload CMS publishing or auto-publish behavior.

## 3. Non-goals

- Do not implement Payload CMS publishing.
- Do not implement Cloudflare R2 uploads.
- Do not implement Plausible analytics UI unless analytics sync is implemented separately.
- Do not modify generated content directly in v1.
- Do not expose this UI publicly without authentication.
- Do not add marketing-style landing pages, hero sections, or decorative layouts.
- Do not build a full CMS replacement.

## 4. Users

Primary user:

- OrbiChat operator or founder reviewing blog-growth agent output.

Secondary future users:

- Content editor reviewing drafts and fact checks.
- Engineer debugging provider failures, budget blocks, and Celery runs.

## 5. Current Backend API Surface

The UI should consume the existing blog-agent backend endpoints:

- `GET /health`
- `GET /runs`
- `GET /runs/{run_id}`
- `POST /runs/daily-scan`
- `POST /runs/weekly-blog-generation`
- `GET /topics`
- `GET /topics/{topic_id}`
- `POST /topics/{topic_id}/approve`
- `POST /topics/{topic_id}/reject`
- `POST /topics/{topic_id}/generate-draft`
- `GET /drafts`
- `GET /drafts/{draft_id}`
- `POST /drafts/{draft_id}/publish-judgment`
- `GET /drafts/{draft_id}/safety-report`
- `GET /costs/summary`
- `GET /costs/runs/{run_id}`

Known backend gaps for ideal UI:

- No current API endpoint lists sources by draft.
- No current API endpoint lists fact checks by draft except summarized safety report.
- No current API endpoint lists social posts by draft.
- No current endpoint exposes raw LLM/search call logs by run.

The v1 UI should work with existing endpoints. A follow-up backend API expansion can add detailed source/fact/social/call-log endpoints.

## 6. Information Architecture

Add a Blog Agent admin section under the authenticated app area.

Recommended route:

- `/app/admin/blog-agent`

Top-level tabs:

1. Overview
2. Runs
3. Topics
4. Drafts
5. Costs

Do not replace the existing app admin dashboard unless the project owner explicitly chooses to merge them.

## 7. Overview Page

Purpose:

- Provide a compact operational snapshot and primary actions.

Required content:

- Backend health state.
- Latest daily scan run.
- Latest weekly blog generation run.
- Counts by topic status:
  - candidate
  - approved
  - rejected
  - drafted
  - published
- Draft count.
- Total estimated cost.
- Daily/monthly budget display if available from backend cost data.

Required actions:

- Trigger daily scan.
- Trigger weekly blog generation.
- Refresh all data.

Behavior:

- Trigger actions should show pending/loading state.
- Success should show created `run_id` and `job_id`.
- Failure should show the backend error message.
- The page should poll or refresh run status periodically while a triggered run is active.

## 8. Runs

Purpose:

- Inspect agent run lifecycle, failures, costs, warnings, and metadata.

List view columns:

- Created time.
- Run type.
- Status.
- Started time.
- Finished time.
- Total estimated cost.
- Input tokens.
- Output tokens.
- Error summary.

Filters:

- Run type.
- Status.

Sort:

- Newest first by default.

Detail view:

- Run ID.
- Run type.
- Status badge.
- Started/finished timestamps.
- Duration.
- Cost summary.
- Error message.
- Metadata JSON viewer.
- Provider warnings from metadata, if present.
- Linked topic/draft IDs from metadata, if present.

Actions:

- Refresh.
- Copy run ID.
- Navigate to linked draft if metadata contains `draft_id`.
- Navigate to linked topic if metadata contains `topic_id`.

## 9. Topics

Purpose:

- Review discovered/scored topics and approve or reject them before generation.

List view columns:

- Title.
- Status.
- Recommended flag.
- Total score.
- Trend score.
- OrbiChat relevance score.
- SEO score.
- Conversion score.
- Target keyword.
- Search intent.
- Created time.

Filters:

- Status.
- Recommended only.
- Search by title/keyword.

Detail view:

- Title.
- Target keyword.
- Search intent.
- Summary.
- All scores.
- Reasoning.
- CTA angle.
- Run ID.
- Created/updated timestamps.

Actions:

- Approve topic.
- Reject topic.
- Generate draft for topic.
- Copy topic ID.

Action rules:

- Approve/reject should be disabled while a request is in progress.
- Generate draft should call `POST /topics/{topic_id}/generate-draft`.
- Generate draft should be available for approved or candidate topics, because the backend manual route accepts explicit topic generation.
- If generation succeeds, show run/draft metadata returned by the backend.

## 10. Drafts

Purpose:

- Review generated drafts and their safety state.

List view columns:

- Title.
- Status.
- Publish ready.
- Publish score.
- Target keyword.
- Created time.
- Updated time.

Filters:

- Status.
- Publish ready.
- Search by title/keyword/slug.

Detail view sections:

1. Header
   - Title.
   - Slug.
   - Status.
   - Publish ready badge.
   - Publish score.
   - Target keyword.
   - Created/updated timestamps.

2. Metadata
   - Meta title.
   - Meta description.
   - Outline JSON viewer.
   - SEO JSON viewer.

3. Draft content
   - Render Markdown preview.
   - Show raw Markdown toggle.
   - Copy Markdown action.

4. Safety report
   - Deterministic blockers.
   - Required fixes.
   - Reasoning.
   - Fact-check summary:
     - total
     - supported
     - unsupported
     - unclear
     - opinion
     - high-severity unsupported
     - medium-severity unclear

5. Future detail panels
   - Sources.
   - Fact checks.
   - Social posts.
   - LLM/search call logs.

Actions:

- Refresh draft.
- Rerun publish judgment.
- View safety report.
- Copy draft ID.
- Copy slug.
- Copy Markdown.

Action rules:

- Rerun publish judgment should call `POST /drafts/{draft_id}/publish-judgment`.
- The UI must clearly state that `publish_ready` is review metadata only and does not publish to Payload.
- Do not include a “Publish” button in v1.

## 11. Costs

Purpose:

- Show estimated spend and model/provider usage.

Required content:

- Total estimated cost.
- Total input tokens.
- Total output tokens.
- LLM call count.
- Search call count.
- Model usage table:
  - provider
  - model
  - call count
  - input tokens
  - output tokens
  - estimated cost

Run-specific cost:

- From a run detail page, call `GET /costs/runs/{run_id}`.
- Display the same cost table scoped to that run.

## 12. UX Requirements

Design principles:

- Operational, dense, readable.
- Tables first, detail panels second.
- No marketing hero.
- No decorative cards inside cards.
- Compact status badges.
- Use icons for refresh, copy, approve, reject, run, warning, and cost where available.
- Use existing OrbiChat design system components where possible.

Responsive behavior:

- Desktop is primary.
- Tablet should remain usable.
- Mobile can collapse tables into stacked rows, but does not need feature parity beyond reading and basic actions.

Loading states:

- Table skeleton or simple loading row.
- Button-level pending states for mutations.

Error states:

- Show backend error message.
- Keep previous loaded data visible where possible.
- Provide retry action.

Empty states:

- No runs: show “No runs yet” plus trigger daily scan.
- No topics: show “No topics yet” plus trigger daily scan.
- No drafts: show “No drafts yet” plus link to topics.

## 13. Authentication and Access

The admin UI must be authenticated.

If the existing `orbichat-web` app already has an admin gating pattern, reuse it.

Minimum acceptable v1:

- Route lives under authenticated app shell.
- Access is restricted to existing admin users if the app exposes an admin role/claim.
- If no role/claim exists, hide the route from normal navigation and document that server-side authorization is a follow-up requirement.

Do not rely only on frontend hiding for production authorization.

## 14. API Client Requirements

Use existing frontend backend client utilities where practical:

- `fetchBackendJson`
- `useBackendQuery`
- existing backend URL resolution

For the blog-agent backend, add a separate base URL env var if it is not the same backend as the main OrbiChat app:

- `NEXT_PUBLIC_BLOG_AGENT_API_URL`

If using a separate base URL, add a small typed API client wrapper:

- `listRuns`
- `getRun`
- `triggerDailyScan`
- `triggerWeeklyGeneration`
- `listTopics`
- `approveTopic`
- `rejectTopic`
- `generateDraftForTopic`
- `listDrafts`
- `getDraft`
- `rerunPublishJudgment`
- `getDraftSafetyReport`
- `getCostSummary`
- `getRunCostSummary`

All API calls must surface backend errors as readable UI messages.

## 15. Data Types

The frontend should define TypeScript types matching the backend response schemas.

Core types:

- `RunRead`
- `RunCreateResponse`
- `TopicRead`
- `DraftRead`
- `WeeklyBlogGenerationResult`
- `DraftSafetyReport`
- `FactCheckSummary`
- `CostSummary`
- `ModelUsageSummary`

Type generation from OpenAPI is preferred if convenient, but hand-written types are acceptable for v1 because the API surface is small.

## 16. Backend Follow-up Recommendations

The current backend is sufficient for a v1 admin UI, but the following endpoints would improve the experience:

- `GET /drafts/{draft_id}/sources`
- `GET /drafts/{draft_id}/fact-checks`
- `GET /drafts/{draft_id}/social-posts`
- `GET /runs/{run_id}/llm-calls`
- `GET /runs/{run_id}/search-calls`

These are not required for the first UI implementation.

## 17. Acceptance Criteria

The admin UI is complete when:

- An authenticated operator can open `/app/admin/blog-agent`.
- The Overview page shows health, recent runs, counts, and cost summary.
- The operator can trigger daily scan and weekly generation.
- The operator can list runs and inspect run detail metadata/errors.
- The operator can list topics, approve/reject topics, and generate a draft for a topic.
- The operator can list drafts and inspect draft detail content, metadata, and safety report.
- The operator can rerun publish judgment from a draft detail page.
- The operator can view global and run-specific cost summaries.
- All mutation actions show loading, success, and error states.
- No UI action publishes content to Payload or any public site.
- No files inside the backend `agent` project are required to run the UI except this PRD and the existing API.

## 18. Test Plan

Frontend tests:

- API client unit tests for success and error responses.
- Component tests for runs/topics/drafts table rendering.
- Mutation tests for approve/reject/generate draft/rerun publish judgment.
- Empty/loading/error state tests.

Manual QA:

1. Start blog-agent backend.
2. Open admin UI.
3. Confirm health loads.
4. Trigger daily scan.
5. Approve a topic.
6. Generate a draft.
7. Open draft detail.
8. Rerun publish judgment.
9. Confirm safety report and costs render.

Regression checks:

```bash
npm run lint
npm run build
```

If Playwright is available:

```bash
npx playwright test
```

## 19. Implementation Order

1. Add typed blog-agent API client.
2. Add admin route shell and tabs.
3. Implement Overview.
4. Implement Runs list/detail.
5. Implement Topics list/detail/actions.
6. Implement Drafts list/detail/safety report/actions.
7. Implement Costs view.
8. Add tests.
9. Run lint/build.

## 20. Open Questions

- Should this UI live in the existing `/app/admin` dashboard or as a dedicated `/app/admin/blog-agent` route?
- Does `orbichat-web` already expose an admin role/claim that can gate this route?
- Will the blog-agent backend share the same auth mechanism as the main backend, or should it initially be local/dev-only?
- Should source/fact/social detail endpoints be added before the first UI implementation, or deferred until after the basic admin UI ships?
