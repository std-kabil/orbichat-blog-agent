Expected input variables:
- `seed_query`: original discovery/search query.
- `candidate_titles`: trend or source titles in the cluster.
- `snippets`: source snippets or short descriptions.
- `source_urls`: URLs associated with the cluster.

Task:
Score this trend cluster for organic search opportunity, OrbiChat relevance, conversion potential, and freshness/trend value. Create one practical blog topic that OrbiChat could credibly publish.

Scoring guidance:
- `trend_score`: current interest/freshness based on the cluster, 0-100.
- `orbichat_relevance_score`: fit with a multi-model AI chat platform, 0-100.
- `seo_score`: likely organic search usefulness and keyword clarity, 0-100.
- `conversion_score`: likelihood the reader could naturally care about comparing or using multiple AI models, 0-100.
- `total_score`: balanced overall score, 0-100. Do not make it higher than the evidence supports.

You must return exactly these top-level JSON fields: title, target_keyword, search_intent, trend_score, orbichat_relevance_score, seo_score, conversion_score, total_score, recommended, reasoning, cta_angle.

Validation rules:
- Return valid JSON only. No markdown fences.
- Do not add extra top-level keys.
- Use integer scores from 0 to 100.
- `search_intent` must be one of: `informational`, `commercial`, `navigational`, `comparison`, `tutorial`.
- `recommended` must be a boolean.
- Keep `reasoning` concise and evidence-aware.
- `cta_angle` should be a natural OrbiChat angle, not a hard sell.

Fallback behavior:
- If the cluster is weak or unrelated to OrbiChat, still return a valid object, set conservative scores, set `recommended` to false, and explain the limitation briefly in `reasoning`.
- If the keyword is unclear, use the best plain-language keyword implied by `seed_query` or the strongest title.

Trend cluster input:
