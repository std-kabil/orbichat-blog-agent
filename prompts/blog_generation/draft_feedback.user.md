Expected input variables:
- `topic`: topic object.
- `sources`: source objects with URL, title, publisher, published date, snippet, and type when available.
- `draft`: current draft object.
- `publish_score`: latest publish-readiness score when available.

Task:
Review the draft and produce actionable feedback for regenerating a stronger version with better score potential.

Output format:
- Return valid JSON only, matching the supplied `DraftFeedbackOutput` schema.
- Required fields: `score`, `summary`, `strengths`, `priority_fixes`, `source_and_citation_fixes`, `structure_fixes`, `seo_fixes`, `factual_risk_notes`.

Feedback rules:
- Prioritize fixes that would raise publish-readiness above 85.
- Name missing citations and source gaps clearly.
- Recommend where Markdown links to supplied source URLs should be added.
- Identify thin sections, generic sections, weak examples, missing comparison tables, weak FAQ answers, or unclear OrbiChat CTA placement.
- Identify any unsupported current claims that should be removed or softened.

Validation rules:
- No markdown fences or commentary.
- No extra top-level keys.
- Do not use the em dash character.
