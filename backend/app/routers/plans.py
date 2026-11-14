from fastapi import APIRouter, status

from app.deps import DB, CurrentUser
from app.models import PlanKind
from app.schemas.plan import AgreementDraftIn, AgreementDraftOut, PlanCreate, PlanItemsUpdate, PlanOut, PlanSummary
from app.services import agreement_helper, planning

router = APIRouter(tags=["ai-helpers"])


@router.post("/ai/agreements/draft", response_model=AgreementDraftOut)
def draft_agreement(req: AgreementDraftIn, _: CurrentUser, db: DB) -> AgreementDraftOut:
    """모호한 요청을 조건(분량·범위·수정 횟수·소요 시간)으로 정리하고, 빠진 조건은 질문으로 돌려줘요. 저장은 하지 않아요."""
    return agreement_helper.draft(db, req)


@router.post("/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(req: PlanCreate, user: CurrentUser, db: DB) -> PlanOut:
    plan = planning.create_plan(db, user, req.goal, PlanKind(req.kind))
    db.commit()
    return planning.plan_out(db, plan)


@router.get("/plans", response_model=list[PlanSummary])
def list_plans(user: CurrentUser, db: DB) -> list[PlanSummary]:
    return planning.list_plans(db, user)


@router.get("/plans/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, user: CurrentUser, db: DB) -> PlanOut:
    return planning.plan_out(db, planning.get_plan(db, user, plan_id))


@router.put("/plans/{plan_id}/items", response_model=PlanOut)
def update_items(plan_id: int, req: PlanItemsUpdate, user: CurrentUser, db: DB) -> PlanOut:
    plan = planning.update_items(db, user, plan_id, req)
    db.commit()
    return planning.plan_out(db, plan)
