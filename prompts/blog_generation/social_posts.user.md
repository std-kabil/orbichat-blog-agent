Expected input variables:
- `title`: article title.
- `slug`: article slug.
- `meta_title`: SEO title.
- `meta_description`: SEO description.
- `markdown_content`: full polished article Markdown.
- `notes`: draft notes.

Task:
Create concise platform-specific social posts for this blog draft.

Output format:
- Return valid JSON only, matching the supplied `SocialPostsOutput` schema.
- Required top-level field: `posts`.
- Each post must include: `platform`, `content`, `metadata`.
- Allowed `platform` values: `x`, `linkedin`, `reddit`, `short_announcement`.

Post requirements:
- `x`: under 280 characters.
- `linkedin`: useful professional framing, generally 400-900 characters.
- `reddit`: conversational, non-promotional, suitable for a discussion post.
- `short_announcement`: 1-2 concise sentences.
- Include a natural CTA to read the article or compare models in OrbiChat where relevant.

Validation rules:
- No markdown fences or commentary.
- No extra top-level keys.
- Do not add factual claims not present in the article.
- Avoid clickbait, exaggerated promises, excessive hashtags, and hard-sell language.
- `metadata` must use string values only; use `{}` if not needed.

Fallback behavior:
- If the draft is thin, focus posts on the central reader problem and avoid making specific claims.
- If the article lacks a clear CTA, use a gentle CTA such as "Compare the models in OrbiChat when you want to test them side by side."
