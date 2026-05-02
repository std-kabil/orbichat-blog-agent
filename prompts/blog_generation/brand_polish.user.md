Expected input variables:
- `draft`: article draft object with title, slug, meta fields, Markdown content, and notes.
- `claim_verifications`: verification results with verdicts, severity, source URLs, explanations, and recommended actions.

Task:
Polish this draft using the verification results. Improve clarity, structure, and OrbiChat brand voice while preserving factual meaning.

Output format:
- Return valid JSON only, matching the supplied `BlogDraftOutput` schema.
- Required fields: `title`, `slug`, `meta_title`, `meta_description`, `markdown_content`, `notes`.

Editing rules:
- Apply `remove`, `rewrite`, and `cite` recommendations conservatively.
- Rewrite unsupported or unclear claims so they become cautious, general, or clearly framed as opinion; remove them if that is safer.
- Keep Markdown structure, tables, lists, links, and citation placeholders intact where they remain valid.
- Improve weak openings, filler transitions, repetitive phrasing, and over-broad conclusions.
- Keep the OrbiChat CTA soft and limited.

Validation rules:
- No markdown fences around the JSON.
- No extra top-level keys.
- Do not add new factual claims.
- Do not invent URLs, citations, pricing, benchmarks, or source names.
- Keep `slug` lowercase, hyphenated, and URL-safe.
- Do not use the em dash character.

Fallback behavior:
- If verification results are missing, make only style/clarity edits and state in `notes` that factual edits were limited by missing verification data.
- If a claim is high severity and unsupported, remove it rather than softening it.
