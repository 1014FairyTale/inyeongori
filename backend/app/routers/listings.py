from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import LISTING_CATEGORIES
from app.deps import DB, CurrentUser
from app.errors import AppError
from app.models import Exchange, ExchangeStatus, Listing, ListingStatus, User
from app.schemas.market import ListingCreate, ListingOut, ListingPage, ListingUpdate, UserBrief
from app.services.embeddings import embed_listing

router = APIRouter(prefix="/listings", tags=["listings"])


def _completed_counts(db: Session, listing_ids: list[int]) -> dict[int, int]:
    if not listing_ids:
        return {}
    rows = db.execute(
        select(Exchange.listing_id, func.count())
        .where(Exchange.listing_id.in_(listing_ids), Exchange.status == ExchangeStatus.COMPLETED)
        .group_by(Exchange.listing_id)
    ).all()
    return {lid: n for lid, n in rows}


def _out(listing: Listing, provider: User, completed: int = 0) -> ListingOut:
    return ListingOut(
        id=listing.id,
        title=listing.title,
        description=listing.description,
        category=listing.category,
        price_tokens=listing.price_tokens,
        est_minutes=listing.est_minutes,
        status=listing.status,
        provider=UserBrief.model_validate(provider),
        created_at=listing.created_at,
        completed_count=completed,
    )


@router.get("/categories", response_model=list[str])
def categories() -> list[str]:
    return LISTING_CATEGORIES


@router.get("", response_model=ListingPage)
def list_listings(
    db: DB,
    q: Annotated[str | None, Query(max_length=50)] = None,
    category: str | None = None,
    provider_id: int | None = None,
    include_paused: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ListingPage:
    stmt = select(Listing, User).join(User, User.id == Listing.provider_id)
    if not (include_paused and provider_id is not None):
        stmt = stmt.where(Listing.status == ListingStatus.ACTIVE)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Listing.title.ilike(like), Listing.description.ilike(like)))
    if category:
        stmt = stmt.where(Listing.category == category)
    if provider_id is not None:
        stmt = stmt.where(Listing.provider_id == provider_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(Listing.created_at.desc(), Listing.id.desc()).offset((page - 1) * size).limit(size)).all()
    counts = _completed_counts(db, [listing.id for listing, _ in rows])
    return ListingPage(
        items=[_out(listing, user, counts.get(listing.id, 0)) for listing, user in rows],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
def create_listing(req: ListingCreate, user: CurrentUser, db: DB) -> ListingOut:
    listing = Listing(provider_id=user.id, **req.model_dump())
    db.add(listing)
    embed_listing(listing)  # 시세 제안·매칭용. 실패해도 등록은 진행돼요.
    db.commit()
    db.refresh(listing)
    return _out(listing, user)


def _get(db: Session, listing_id: int) -> tuple[Listing, User]:
    row = db.execute(
        select(Listing, User).join(User, User.id == Listing.provider_id).where(Listing.id == listing_id)
    ).first()
    if row is None:
        raise AppError("NOT_FOUND", "재능 상품을 찾을 수 없어요", 404)
    return row[0], row[1]


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: DB) -> ListingOut:
    listing, provider = _get(db, listing_id)
    return _out(listing, provider, _completed_counts(db, [listing.id]).get(listing.id, 0))


@router.patch("/{listing_id}", response_model=ListingOut)
def update_listing(listing_id: int, req: ListingUpdate, user: CurrentUser, db: DB) -> ListingOut:
    listing, provider = _get(db, listing_id)
    if listing.provider_id != user.id:
        raise AppError("FORBIDDEN", "내 상품만 수정할 수 있어요", 403)
    changes = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    for k, v in changes.items():
        setattr(listing, k, v)
    if changes.keys() & {"title", "description", "category"}:
        embed_listing(listing)
    db.commit()
    db.refresh(listing)
    return _out(listing, provider, _completed_counts(db, [listing.id]).get(listing.id, 0))
