from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_database_session
from repositories.costs import summarize_costs
from schemas.cost import CostSummary

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("/summary", response_model=CostSummary)
def read_cost_summary(
    db: Session = Depends(get_database_session),
) -> CostSummary:
    return summarize_costs(db)


@router.get("/runs/{run_id}", response_model=CostSummary)
def read_run_cost_summary(
    run_id: UUID,
    db: Session = Depends(get_database_session),
) -> CostSummary:
    return summarize_costs(db, run_id=run_id)
