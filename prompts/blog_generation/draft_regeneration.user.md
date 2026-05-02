Expected input variables:
- `topic`: topic object.
- `sources`: source objects with URL, title, publisher, published date, snippet, and type when available.
- `current_draft`: saved draft object to improve.
- `feedback`: editorial feedback object.
- `additional_instructions`: optional admin instructions.

Task:
Regenerate the draft as a new improved version. Apply the feedback and any additional admin instructions while staying factual and source-aware.

Output format:
- Return valid JSON only, matching the supplied `BlogDraftOutput` schema.
- Required fields: `title`, `slug`, `meta_title`, `meta_description`, `markdown_content`, `notes`.

Regeneration rules:
- Keep the same topic and search intent.
- Improve weak sections, source coverage, examples, headings, CTA fit, and SEO clarity.
- Add citations as Markdown links using only supplied source URLs.
- Add a `## Sources` section when the article uses source-backed factual claims.
- Remove or soften unsupported claims.
- Keep the slug lowercase, hyphenated, and URL-safe.

Validation rules:
- No markdown fences around the JSON.
- No extra top-level keys.
- Do not include placeholder text, TODOs, "citation needed", fake footnotes, or fake links.
- Do not use the em dash character.
