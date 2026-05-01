Expected input variables:
- `draft`: polished article draft object.
- `deterministic_blockers`: deterministic publish blockers from application rules.
- `claim_verifications`: claim verification results.

Task:
Judge whether this draft is ready for publication review. This model judgment is combined with deterministic rules; you must not override blocked conditions.

Output format:
- Return valid JSON only, matching the supplied `PublishJudgmentOutput` schema.
- Required fields: `publish_ready`, `score`, `risk_level`, `required_fixes`, `reasoning`.

Decision rules:
- If `deterministic_blockers` is non-empty, set `publish_ready` to false.
- If `AUTO_PUBLISH is false` appears in deterministic blockers, set `publish_ready` to false.
- If any high-severity unsupported claim exists, set `publish_ready` to false and include a required fix.
- If pricing or benchmark claims are unsupported or unclear, set `publish_ready` to false unless they are clearly opinion/non-factual.
- Score should reflect readiness for publication review, not model confidence.
- A score of 85+ should require strong usefulness, low factual risk, clean brand fit, and no blockers.

Validation rules:
- No markdown fences or commentary.
- No extra top-level keys.
- `score` must be an integer from 0 to 100.
- `risk_level` must be one of: `low`, `medium`, `high`.
- `required_fixes` must be an array of specific editor actions.
- Keep `reasoning` short and concrete.

Fallback behavior:
- If verification data is missing, set `publish_ready` to false unless the article contains no factual claims, lower the score, and require verification.
- If the draft is empty or malformed, set `publish_ready` to false, `risk_level` to `high`, and list the structural fix needed.
