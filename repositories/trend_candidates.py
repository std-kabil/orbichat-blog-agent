from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TrendCandidate
from schemas.trend import TrendCandidateCreate


def create_trend_candidate(db: Session, candidate: TrendCandidateCreate) -> TrendCandidate:
    trend_candidate = TrendCandidate(
        run_id=candidate.run_id,
        title=candidate.title,
        query=candidate.query,
        source=candidate.source.value,
        url=candidate.url,
        snippet=candidate.snippet,
        detected_at=candidate.detected_at,
        raw_score=candidate.raw_score,
        metadata_json=candidate.metadata_json,
    )
    db.add(trend_candidate)
    db.commit()
    db.refresh(trend_candidate)
    return trend_candidate


def create_trend_candidates(
    db: Session,
    candidates: Iterable[TrendCandidateCreate],
) -> list[TrendCandidate]:
    trend_candidates = [
        TrendCandidate(
            run_id=candidate.run_id,
            title=candidate.title,
            query=candidate.query,
            source=candidate.source.value,
            url=candidate.url,
            snippet=candidate.snippet,
            detected_at=candidate.detected_at,
            raw_score=candidate.raw_score,
            metadata_json=candidate.metadata_json,
        )
        for candidate in candidates
    ]
    db.add_all(trend_candidates)
    db.commit()
    for trend_candidate in trend_candidates:
        db.refresh(trend_candidate)
    return trend_candidates


def list_trend_candidates_by_run(db: Session, run_id: UUID) -> list[TrendCandidate]:
    statement = (
        select(TrendCandidate)
        .where(TrendCandidate.run_id == run_id)
        .order_by(TrendCandidate.created_at.asc())
    )
    return list(db.scalars(statement).all())
