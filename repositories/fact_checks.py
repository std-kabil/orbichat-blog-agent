from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FactCheck
from schemas.workflow import ClaimVerificationOutput


def create_fact_checks_from_verifications(
    db: Session,
    *,
    draft_id: UUID,
    verifications: Iterable[ClaimVerificationOutput],
) -> list[FactCheck]:
    fact_checks = [
        FactCheck(
            draft_id=draft_id,
            claim=verification.claim,
            claim_type=verification.claim_type,
            verdict=verification.verdict,
            severity=verification.severity,
            explanation=verification.explanation,
            source_urls_json=verification.source_urls,
            recommended_action=verification.recommended_action,
        )
        for verification in verifications
    ]
    db.add_all(fact_checks)
    db.commit()
    for fact_check in fact_checks:
        db.refresh(fact_check)
    return fact_checks


def list_fact_checks_by_draft(db: Session, draft_id: UUID) -> list[FactCheck]:
    statement = select(FactCheck).where(FactCheck.draft_id == draft_id).order_by(FactCheck.created_at.asc())
    return list(db.scalars(statement).all())
