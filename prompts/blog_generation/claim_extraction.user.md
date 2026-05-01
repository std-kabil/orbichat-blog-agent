Expected input variables:
- `title`: article title.
- `slug`: article slug.
- `meta_title`: SEO title.
- `meta_description`: SEO description.
- `markdown_content`: full article Markdown.
- `notes`: drafting notes.

Task:
Extract factual claims that need fact checking or risk review from `markdown_content`.

Output format:
- Return valid JSON only, matching the supplied `ClaimExtractionOutput` schema.
- Required top-level field: `claims`.
- Each claim must include: `claim`, `claim_type`, `risk_level`, `needs_verification`.

Extraction rules:
- Include factual claims about products, model capabilities, features, availability, pricing, rankings, benchmarks, dates, current events, and named competitors.
- Include claims that depend on supplied sources or could become stale.
- Include exact article wording in `claim` when possible; if the article sentence contains multiple claims, split it into atomic claims.
- Do not extract purely rhetorical language, headings alone, generic advice, or OrbiChat CTA copy unless it contains a factual product claim.

Validation rules:
- No markdown fences or commentary.
- No extra top-level keys.
- Allowed `claim_type` values: `pricing`, `benchmark`, `news`, `product_feature`, `general`, `opinion`.
- Allowed `risk_level` values: `low`, `medium`, `high`.
- Set `needs_verification` true for all pricing, benchmark, news, product feature, availability, ranking, and competitor-comparison claims.

Fallback behavior:
- If the article is empty or has no factual claims, return `{"claims":[]}`.
- If a claim is ambiguous, include it as `general`, set `risk_level` to `medium`, and set `needs_verification` to true.
