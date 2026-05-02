from typing import Literal
from uuid import UUID

from pydantic import Field

from schemas.common import APIModel

ClaimType = Literal["pricing", "benchmark", "news", "product_feature", "general", "opinion"]
RiskLevel = Literal["low", "medium", "high"]
VerificationVerdict = Literal["supported", "unsupported", "unclear", "opinion"]
RecommendedAction = Literal["keep", "cite", "rewrite", "remove"]


class SEOAnglesOutput(APIModel):
    primary_angle: str
    alternative_angles: list[str] = Field(default_factory=list)
    target_audience: str
    search_intent: str
    primary_keyword: str
    secondary_keywords: list[str] = Field(default_factory=list)
    recommended_title: str
    meta_description: str
    cta_strategy: str


class OutlineSection(APIModel):
    heading: str
    goal: str
    key_points: list[str] = Field(default_factory=list)


class OutlineFAQ(APIModel):
    question: str
    answer_goal: str


class OutlineOutput(APIModel):
    title: str
    slug: str
    meta_title: str
    meta_description: str
    sections: list[OutlineSection] = Field(default_factory=list)
    faq: list[OutlineFAQ] = Field(default_factory=list)
    internal_links: list[str] = Field(default_factory=list)
    cta_placements: list[str] = Field(default_factory=list)


class BlogDraftOutput(APIModel):
    title: str
    slug: str
    meta_title: str
    meta_description: str
    markdown_content: str
    notes: str


class DraftFeedbackOutput(APIModel):
    score: int = Field(ge=0, le=100)
    summary: str
    strengths: list[str] = Field(default_factory=list)
    priority_fixes: list[str] = Field(default_factory=list)
    source_and_citation_fixes: list[str] = Field(default_factory=list)
    structure_fixes: list[str] = Field(default_factory=list)
    seo_fixes: list[str] = Field(default_factory=list)
    factual_risk_notes: list[str] = Field(default_factory=list)


class DraftRegenerateRequest(APIModel):
    additional_instructions: str | None = Field(default=None, max_length=4000)


class DraftRegenerationResult(APIModel):
    parent_draft_id: UUID
    draft_id: UUID
    topic_id: UUID
    version: int
    feedback: DraftFeedbackOutput
    publish_ready: bool = False
    publish_score: int | None = None


class ExtractedClaim(APIModel):
    claim: str
    claim_type: ClaimType
    risk_level: RiskLevel
    needs_verification: bool


class ClaimExtractionOutput(APIModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)


class ClaimVerificationOutput(APIModel):
    claim: str
    claim_type: ClaimType | None = None
    verdict: VerificationVerdict
    severity: RiskLevel
    source_urls: list[str] = Field(default_factory=list)
    explanation: str
    recommended_action: RecommendedAction


class ClaimVerificationBatchOutput(APIModel):
    verifications: list[ClaimVerificationOutput] = Field(default_factory=list)


class PublishJudgmentOutput(APIModel):
    publish_ready: bool
    score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    required_fixes: list[str] = Field(default_factory=list)
    reasoning: str


class SocialPostDraft(APIModel):
    platform: str
    content: str
    metadata: dict[str, str] = Field(default_factory=dict)


class SocialPostsOutput(APIModel):
    posts: list[SocialPostDraft] = Field(default_factory=list)


class DeterministicPublishChecks(APIModel):
    publish_ready: bool
    blockers: list[str] = Field(default_factory=list)


class FactCheckSummary(APIModel):
    total: int
    supported: int
    unsupported: int
    unclear: int
    opinion: int
    high_severity_unsupported: int
    medium_severity_unclear: int


class DraftSafetyReport(APIModel):
    draft_id: UUID
    publish_ready: bool
    publish_score: int | None
    deterministic_blockers: list[str] = Field(default_factory=list)
    required_fixes: list[str] = Field(default_factory=list)
    fact_check_summary: FactCheckSummary
    reasoning: str | None = None


class WeeklyBlogGenerationResult(APIModel):
    run_id: UUID
    topic_id: UUID | None
    draft_id: UUID | None
    status: Literal["completed", "failed"]
    warnings: list[str] = Field(default_factory=list)
    provider_warnings: list[str] = Field(default_factory=list)
    publish_ready: bool = False
    publish_score: int | None = None
