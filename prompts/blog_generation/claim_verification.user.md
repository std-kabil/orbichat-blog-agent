Expected input variables:
- `claims`: extracted claims with type, risk level, and verification requirement.
- `sources`: source objects with URL, title, publisher, published date, snippet, and type when available.

Task:
Verify each claim against the supplied source snippets and recommend the safest editorial action.

Output format:
- Return valid JSON only, matching the supplied `ClaimVerificationBatchOutput` schema.
- Required top-level field: `verifications`.
- Each verification must include: `claim`, `claim_type`, `verdict`, `severity`, `source_urls`, `explanation`, `recommended_action`.

Decision rules:
- `supported`: source snippets directly support the claim.
- `unsupported`: snippets contradict the claim or there is no relevant support.
- `unclear`: snippets are relevant but incomplete, ambiguous, outdated, or not specific enough.
- `opinion`: the claim is subjective and should not be fact-checked as factual.
- `keep`: safe to keep without citation, usually low-risk general or opinion.
- `cite`: keep but cite one or more supplied source URLs.
- `rewrite`: claim may be usable only if softened, narrowed, or made less specific.
- `remove`: claim is risky and unsupported, contradicted, or unverifiable from provided sources.

Validation rules:
- No markdown fences or commentary.
- No extra top-level keys.
- Use only supplied source URLs in `source_urls`.
- Use empty arrays for `source_urls` when no source applies.
- Pricing, benchmark, ranking, availability, and product feature claims require direct support to be `supported`.

Fallback behavior:
- If `claims` is empty, return `{"verifications":[]}`.
- If sources are empty, mark factual claims as `unclear` or `unsupported` according to risk, set `source_urls` to [], and recommend `rewrite` or `remove`.
