Expected input variables:
- `topic`: approved topic object.
- `sources`: source objects with URL, title, publisher, published date, snippet, and type when available.
- `seo_angles`: SEO brief.
- `outline`: approved outline with title, slug, sections, FAQ, internal links, and CTA placements.

Task:
Write the complete article draft in Markdown using the supplied outline and source context. The article should attract relevant visitors to OrbiChat by being useful, factual, specific, and search-aligned.

Output format:
- Return valid JSON only, matching the supplied `BlogDraftOutput` schema.
- Required fields: `title`, `slug`, `meta_title`, `meta_description`, `markdown_content`, `notes`.
- `markdown_content` must contain the article in Markdown.

Article acceptance criteria:
- Open with the reader's problem or decision, not a generic AI preamble.
- Use the outline as the structure unless a small adjustment improves clarity.
- Include practical examples or workflows relevant to the target audience.
- Include a comparison table when the topic involves choosing between models, tools, apps, or workflows.
- Include FAQ content only if the outline asks for it and it adds value.
- Use concise headings and direct explanations.
- Include one natural OrbiChat CTA where relevant, for example: "OrbiChat lets you compare multiple AI models in one place."
- Keep OrbiChat mentions restrained and contextually useful.

Validation rules:
- No markdown fences around the JSON.
- No extra top-level keys.
- Do not invent citations or URLs.
- Add citations as Markdown links using only supplied source URLs when a factual claim depends on source context.
- Include a short `## Sources` section when the article uses source-backed factual claims.
- Do not include placeholder text, TODOs, or "citation needed".
- Do not make unsupported claims about pricing, benchmarks, product availability, legal/medical/financial outcomes, or competitor capabilities.
- If sources are insufficient for a factual claim, omit the claim or make the uncertainty clear.
- Keep `slug` lowercase, hyphenated, and URL-safe.
- Put source gaps, uncertainty, and notable exclusions in `notes`.
- Do not use the em dash character.

Fallback behavior:
- If sources are missing or weak, write an evergreen practical guide that avoids current factual claims and state the limitation in `notes`.
- If the outline is thin, create a better article structure while staying within the topic and SEO angle.
- If the topic is too broad, focus on the audience and primary keyword from `seo_angles`.
