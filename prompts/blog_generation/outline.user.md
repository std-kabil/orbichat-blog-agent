Expected input variables:
- `topic`: approved topic object.
- `sources`: source objects with URL, title, publisher, published date, snippet, and type when available.
- `seo_angles`: SEO brief with angle, audience, keywords, title, meta description, and CTA strategy.

Task:
Create a long-form article outline from the topic, sources, and SEO angle. The output will be used directly by the article draft model.

Output format:
- Return valid JSON only, matching the supplied `OutlineOutput` schema.
- Required fields: `title`, `slug`, `meta_title`, `meta_description`, `sections`, `faq`, `internal_links`, `cta_placements`.
- Each `sections` item must include: `heading`, `goal`, `key_points`.
- Each `faq` item must include: `question`, `answer_goal`.

Validation rules:
- No markdown fences or commentary.
- No extra top-level keys.
- `sections` should usually contain 5-9 useful sections.
- `key_points` must be concrete enough for article drafting.
- `meta_description` should be concise and honest.
- `internal_links` should use plain route suggestions or page names, not invented URLs.
- `cta_placements` should describe where a soft OrbiChat mention belongs.

Fallback behavior:
- If sources are thin, include a section that keeps claims cautious and practical.
- If the SEO angle is broad, narrow the outline around the stated target audience and primary keyword.
