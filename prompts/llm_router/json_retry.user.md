Your previous response did not satisfy the {model_name} schema.

Expected input variables:
- `model_name`: the Pydantic output model that must validate.
- `parse_error`: the validation or JSON parsing error from the previous attempt.
- Previous assistant message: the invalid JSON or non-JSON response to repair.

Validation errors:
{parse_error}

Repair the response now.

Rules:
- Reply with one corrected JSON object only.
- Do not wrap it in markdown fences.
- Do not add commentary, apologies, or explanations.
- Use the exact field names from the {model_name} schema.
- Do not add extra top-level keys.
- Preserve the meaning of the attempted response as much as possible.
- Do not add new facts, sources, citations, claims, or creative content to make validation easier.
- Respect all field types, required fields, enum values, and score ranges.
- Use empty arrays or empty objects when the schema allows them.
- Use null only when the schema explicitly allows null.
