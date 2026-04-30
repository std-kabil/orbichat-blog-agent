import re
from collections.abc import Sequence

from app.config import Settings
from schemas.workflow import ClaimVerificationOutput, DeterministicPublishChecks

PLACEHOLDER_PATTERNS = (
    "TODO",
    "TBD",
    "[insert",
    "{{",
    "lorem ipsum",
)

FAKE_CITATION_PATTERN = re.compile(r"\[(?:source|citation needed|\d+)\]", re.IGNORECASE)
CLICKBAIT_TERMS = ("shocking", "you won't believe", "insane", "secret trick")
ORBITCHAT_CTA_PATTERN = re.compile(r"\b(?:try|use|visit|sign up for)\s+orbichat\b", re.IGNORECASE)


def run_deterministic_publish_checks(
    *,
    settings: Settings,
    title: str,
    slug: str,
    meta_description: str | None,
    markdown_content: str,
    verifications: Sequence[ClaimVerificationOutput],
) -> DeterministicPublishChecks:
    blockers: list[str] = []
    word_count = len(re.findall(r"\b[\w'-]+\b", markdown_content))

    if word_count < 900:
        blockers.append("Article has fewer than 900 words")
    if not _has_supported_sources(verifications):
        blockers.append("Article has no supported sources for factual claims")
    if any(v.severity == "high" and v.verdict == "unsupported" for v in verifications):
        blockers.append("Article has a high-severity unsupported claim")
    if sum(1 for v in verifications if v.severity == "medium" and v.verdict == "unclear") > 2:
        blockers.append("Article has more than 2 medium-severity unclear claims")
    if len(ORBITCHAT_CTA_PATTERN.findall(markdown_content)) > 3:
        blockers.append("OrbiChat CTA appears more than 3 times")
    if not title.strip() or any(term in title.lower() for term in CLICKBAIT_TERMS):
        blockers.append("Title is empty or too clickbait-like")
    if not meta_description or not meta_description.strip():
        blockers.append("Meta description is missing")
    if not slug.strip():
        blockers.append("Slug is missing")
    if any(pattern.lower() in markdown_content.lower() for pattern in PLACEHOLDER_PATTERNS):
        blockers.append("Article contains placeholder text")
    if "as an ai language model" in markdown_content.lower():
        blockers.append('Article says "as an AI language model"')
    if FAKE_CITATION_PATTERN.search(markdown_content):
        blockers.append("Article uses fake citations")
    if _has_unverified_pricing_or_benchmark(verifications):
        blockers.append("Article includes direct pricing/benchmark claims without source verification")
    if not settings.auto_publish:
        blockers.append("AUTO_PUBLISH is false")

    return DeterministicPublishChecks(publish_ready=not blockers, blockers=blockers)


def _has_supported_sources(verifications: Sequence[ClaimVerificationOutput]) -> bool:
    return any(
        verification.verdict == "supported" and bool(verification.source_urls)
        for verification in verifications
    )


def _has_unverified_pricing_or_benchmark(verifications: Sequence[ClaimVerificationOutput]) -> bool:
    return any(
        (
            verification.claim_type in {"pricing", "benchmark"}
            or "pricing" in verification.explanation.lower()
            or "benchmark" in verification.explanation.lower()
        )
        and verification.verdict != "supported"
        for verification in verifications
    )
