"""부탁 쪼개기 (기능 5). 목표 기반 교환 경로(기능 7)는 6단계에서 이 로직을 재사용해요."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai.schemas import BreakdownAI
from ai.structured import generate
from app.core.constants import LISTING_CATEGORIES
from app.errors import AppError
from app.models import Listing, Plan, PlanItem, PlanKind, PriceBasis, User
from app.schemas.plan import LinkedListing, PlanItemOut, PlanItemsUpdate, PlanOut, PlanSummary
from app.services.pricing import market_stats, market_stats_text, suggest_price

FALLBACK_CATEGORY = "생활·기타"


def _item_text(title: str, description: str | None) -> str:
    return f"{title}: {description or ''}".strip()


def create_breakdown(db: Session, user: User, goal: str) -> Plan:
    stats = market_stats(db)
    prompt = "\n".join(
        [
            "## 목표",
            goal,
            "",
            "## 사용할 수 있는 카테고리",
            ", ".join(LISTING_CATEGORIES),
            "",
            "## 마켓 가격 정보",
            market_stats_text(stats),
        ]
    )
    ai = generate("breakdown", prompt, BreakdownAI)

    plan = Plan(user_id=user.id, goal=goal, kind=PlanKind.BREAKDOWN, summary=ai.summary)
    db.add(plan)
    db.flush()
    for i, it in enumerate(ai.items):
        category = it.category if it.category in LISTING_CATEGORIES else FALLBACK_CATEGORY
        price = suggest_price(
            db,
            _item_text(it.title, it.description),
            category=category,
            ai_estimate=it.estimated_tokens,
            exclude_user_id=user.id,
            stats=stats,
        )
        db.add(
            PlanItem(
                plan_id=plan.id,
                position=i,
                title=it.title[:60],
                description=it.description,
                minutes=it.minutes,
                category=category,
                suggested_tokens=price.tokens,
                price_basis=price.basis,
                similar_count=price.similar_count,
                linked_listing_id=price.best_listing_id,
                ai_generated=True,
            )
        )
    db.flush()
    return plan


def get_plan(db: Session, user: User, plan_id: int) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise AppError("NOT_FOUND", "계획을 찾을 수 없어요", 404)
    return plan


def items_of(db: Session, plan_id: int) -> list[PlanItem]:
    return list(db.scalars(select(PlanItem).where(PlanItem.plan_id == plan_id).order_by(PlanItem.position)))


def update_items(db: Session, user: User, plan_id: int, req: PlanItemsUpdate) -> Plan:
    """사용자가 활동을 수정·삭제·추가한 결과를 통째로 반영해요."""
    plan = get_plan(db, user, plan_id)
    existing = {it.id: it for it in items_of(db, plan.id)}
    keep: set[int] = set()

    for pos, inp in enumerate(req.items):
        it = existing.get(inp.id) if inp.id is not None else None
        if it is None:  # 새 활동
            if inp.suggested_tokens is not None:
                tokens, basis, similar, best = inp.suggested_tokens, PriceBasis.USER, 0, None
            else:
                p = suggest_price(
                    db, _item_text(inp.title, inp.description), category=inp.category, ai_estimate=None, exclude_user_id=user.id
                )
                tokens, basis, similar, best = p.tokens, p.basis, p.similar_count, p.best_listing_id
            it = PlanItem(
                plan_id=plan.id,
                position=pos,
                title=inp.title,
                description=inp.description,
                minutes=inp.minutes,
                category=inp.category,
                suggested_tokens=tokens,
                price_basis=basis,
                similar_count=similar,
                linked_listing_id=best,
                ai_generated=False,
                edited=True,
            )
            db.add(it)
            db.flush()
        else:
            changed = (it.title, it.description, it.minutes, it.category) != (
                inp.title,
                inp.description,
                inp.minutes,
                inp.category,
            )
            if inp.suggested_tokens is not None and inp.suggested_tokens != it.suggested_tokens:
                it.suggested_tokens = inp.suggested_tokens
                it.price_basis = PriceBasis.USER
                changed = True
            it.position, it.title, it.description, it.minutes, it.category = (
                pos,
                inp.title,
                inp.description,
                inp.minutes,
                inp.category,
            )
            it.edited = it.edited or changed
        keep.add(it.id)

    for item_id, it in existing.items():
        if item_id not in keep:
            db.delete(it)
    db.flush()
    return plan


# ---- 응답 ----

def plan_out(db: Session, plan: Plan) -> PlanOut:
    items = items_of(db, plan.id)
    listing_ids = [it.linked_listing_id for it in items if it.linked_listing_id]
    linked: dict[int, LinkedListing] = {}
    if listing_ids:
        rows = db.execute(
            select(Listing, User.nickname).join(User, User.id == Listing.provider_id).where(Listing.id.in_(listing_ids))
        ).all()
        linked = {
            listing.id: LinkedListing(id=listing.id, title=listing.title, price_tokens=listing.price_tokens, provider_nickname=nick)
            for listing, nick in rows
        }
    out_items = [
        PlanItemOut(
            id=it.id,
            position=it.position,
            title=it.title,
            description=it.description,
            minutes=it.minutes,
            category=it.category,
            suggested_tokens=it.suggested_tokens,
            price_basis=it.price_basis,
            similar_count=it.similar_count,
            linked_listing=linked.get(it.linked_listing_id) if it.linked_listing_id else None,
            ai_generated=it.ai_generated,
            edited=it.edited,
        )
        for it in items
    ]
    return PlanOut(
        id=plan.id,
        goal=plan.goal,
        kind=plan.kind,
        summary=plan.summary,
        items=out_items,
        total_tokens=sum(i.suggested_tokens for i in out_items),
        created_at=plan.created_at,
    )


def list_plans(db: Session, user: User) -> list[PlanSummary]:
    rows = db.execute(
        select(Plan, func.count(PlanItem.id), func.coalesce(func.sum(PlanItem.suggested_tokens), 0))
        .outerjoin(PlanItem, PlanItem.plan_id == Plan.id)
        .where(Plan.user_id == user.id)
        .group_by(Plan.id)
        .order_by(Plan.created_at.desc(), Plan.id.desc())
    ).all()
    return [
        PlanSummary(id=p.id, goal=p.goal, kind=p.kind, item_count=n, total_tokens=int(total), created_at=p.created_at)
        for p, n, total in rows
    ]
