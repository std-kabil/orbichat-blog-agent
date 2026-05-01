Expected input variables:
- `topic`: approved topic object with title, target keyword, intent, summary, scores, reasoning, and CTA angle.
- `sources`: research/source objects with URL, title, publisher, date, snippet, and source type when available.

Task:
Generate the strongest SEO angle for this weekly OrbiChat blog topic. The output will feed the outline generator, so make it specific and actionable.

Output format:
- Return valid JSON only, matching the supplied `SEOAnglesOutput` schema.
- Required fields: `primary_angle`, `alternative_angles`, `target_audience`, `search_intent`, `primary_keyword`, `secondary_keywords`, `recommended_title`, `meta_description`, `cta_strategy`.

Validation rules:
- No markdown fences or commentary.
- No extra top-level keys.
- `alternative_angles` and `secondary_keywords` must be arrays.
- `meta_description` should be under 160 characters when practical.
- `recommended_title` should be specific, honest, and not clickbait.
- `cta_strategy` should softly connect to comparing multiple AI models in OrbiChat when relevant.

Fallback behavior:
- If sources are missing or weak, avoid newsy/current claims and produce an evergreen angle.
- If the topic is broad, narrow it to one clear audience and search intent.
- If the OrbiChat connection is weak, keep the CTA light and practical rather than promotional.
