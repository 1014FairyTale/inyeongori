"""후기 보너스 산정 (결정 사항 D5-A).

AI는 기여도 점수와 근거만 판단하고, 금액은 아래 규칙으로 계산해요. 모든 단계를 adjustments에 기록해요.

1. 지급 조건: 기여도 ≥ 70, 별점 ≥ 4, 후기 글자 수 ≥ 20
2. 기본 금액: 70~84점 거래가의 10%, 85점 이상 20% (최소 1토큰)
3. 거래당 상한 10토큰
4. 같은 두 사람의 30일 내 반복 거래: 2번째 50%, 3번째부터 0
5. 제공자당 하루 상한 30토큰 (한국 시간 기준)
6. 보너스 풀 잔액을 넘지 않음
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    BONUS_MAX_TOKENS_PER_EXCHANGE,
    BONUS_MAX_TOKENS_PER_PROVIDER_PER_DAY,
    BONUS_MIN_CONTRIBUTION_SCORE,
    BONUS_MIN_RATING,
    BONUS_MIN_REVIEW_CHARS,
    BONUS_MIN_TOKENS,
    BONUS_TIERS,
    REPEAT_PAIR_MULTIPLIERS,
    REPEAT_PAIR_WINDOW_DAYS,
    REVIEW_DEADLINE_DAYS,
    REVIEW_REWARD_MIN_CHARS,
    REVIEW_REWARD_MIN_QUALITY,
    REVIEW_REWARD_MIN_TOKENS,
    REVIEW_REWARD_RATE,
)
from app.models import AccountKind, EntryType, Exchange, ExchangeStatus, Review, ReviewAnalysis, TokenAccount
from app.services import ledger

KST = timezone(timedelta(hours=9))


@dataclass
class BonusDecision:
    eligible: bool
    base: int
    final: int
    adjustments: list[dict[str, Any]] = field(default_factory=list)


def _note(adj: list[dict[str, Any]], rule: str, message: str, before: int | None = None, after: int | None = None) -> None:
    adj.append({"rule": rule, "message": message, "before": before, "after": after})


def repeat_ordinal(db: Session, ex: Exchange) -> int:
    """같은 두 사람(방향 무관)이 최근 30일 안에 완료한 거래 중 이 거래가 몇 번째인지."""
    completed_at = ex.completed_at or datetime.now(UTC)
    since = completed_at - timedelta(days=REPEAT_PAIR_WINDOW_DAYS)
    a, b = ex.requester_id, ex.provider_id
    pair = or_(
        and_(Exchange.requester_id == a, Exchange.provider_id == b),
        and_(Exchange.requester_id == b, Exchange.provider_id == a),
    )
    n = db.scalar(
        select(func.count())
        .select_from(Exchange)
        .where(
            pair,
            Exchange.status == ExchangeStatus.COMPLETED,
            Exchange.completed_at >= since,
            (Exchange.completed_at < completed_at) | ((Exchange.completed_at == completed_at) & (Exchange.id <= ex.id)),
        )
    )
    return int(n or 1)


def given_today(db: Session, provider_id: int, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    start_kst = now.astimezone(KST).replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.scalar(
        select(func.coalesce(func.sum(ReviewAnalysis.final_bonus), 0)).where(
            ReviewAnalysis.reviewee_id == provider_id, ReviewAnalysis.created_at >= start_kst
        )
    )
    return int(total or 0)


def decide(db: Session, ex: Exchange, review: Review, score: int) -> BonusDecision:
    adj: list[dict[str, Any]] = []
    text_len = len((review.good_text or "").strip()) + len((review.bad_text or "").strip())

    reasons = []
    if score < BONUS_MIN_CONTRIBUTION_SCORE:
        reasons.append(f"기여도 점수가 {BONUS_MIN_CONTRIBUTION_SCORE}점 미만이에요 ({score}점)")
    if review.rating < BONUS_MIN_RATING:
        reasons.append(f"별점이 {BONUS_MIN_RATING}점 미만이에요 ({review.rating}점)")
    if text_len < BONUS_MIN_REVIEW_CHARS:
        reasons.append(f"후기가 {BONUS_MIN_REVIEW_CHARS}자 미만이에요 ({text_len}자)")
    if reasons:
        for r in reasons:
            _note(adj, "eligibility", r)
        return BonusDecision(False, 0, 0, adj)

    rate = next(r for min_score, r in BONUS_TIERS if score >= min_score)
    base = max(BONUS_MIN_TOKENS, round(ex.price_tokens * rate))
    _note(adj, "tier", f"기여도 {score}점 → 거래가 {ex.price_tokens}토큰의 {int(rate * 100)}%", None, base)
    amount = base

    if amount > BONUS_MAX_TOKENS_PER_EXCHANGE:
        _note(adj, "per_exchange_cap", f"거래당 최대 {BONUS_MAX_TOKENS_PER_EXCHANGE}토큰", amount, BONUS_MAX_TOKENS_PER_EXCHANGE)
        amount = BONUS_MAX_TOKENS_PER_EXCHANGE

    n = repeat_ordinal(db, ex)
    mult = REPEAT_PAIR_MULTIPLIERS[min(n, len(REPEAT_PAIR_MULTIPLIERS)) - 1]
    if mult < 1:
        after = int(amount * mult)
        _note(adj, "repeat_pair", f"최근 {REPEAT_PAIR_WINDOW_DAYS}일 안에 같은 두 사람의 {n}번째 거래 → {int(mult * 100)}%", amount, after)
        amount = after

    if amount > 0:
        remaining = max(0, BONUS_MAX_TOKENS_PER_PROVIDER_PER_DAY - given_today(db, ex.provider_id))
        if amount > remaining:
            _note(adj, "daily_cap", f"제공자당 하루 최대 {BONUS_MAX_TOKENS_PER_PROVIDER_PER_DAY}토큰 (오늘 남은 한도 {remaining})", amount, remaining)
            amount = remaining

    if amount > 0:
        system = ledger.get_system_user(db)
        pool = db.scalar(
            select(TokenAccount)
            .where(TokenAccount.owner_user_id == system.id, TokenAccount.kind == AccountKind.SYSTEM_BONUS_POOL)
            .with_for_update()
        )
        assert pool is not None
        if amount > pool.balance:
            _note(adj, "pool", f"보너스 풀 잔액 부족 ({pool.balance}토큰)", amount, pool.balance)
            amount = pool.balance

    return BonusDecision(True, base, amount, adj)


def _pool_for_update(db: Session) -> TokenAccount:
    system = ledger.get_system_user(db)
    pool = db.scalar(
        select(TokenAccount)
        .where(TokenAccount.owner_user_id == system.id, TokenAccount.kind == AccountKind.SYSTEM_BONUS_POOL)
        .with_for_update()
    )
    assert pool is not None
    return pool


def decide_reviewer_reward(
    db: Session, ex: Exchange, review: Review, quality: int, *, on_time: bool, reserved: int = 0
) -> tuple[int, str]:
    """후기 작성자(요청자) 환급: 기한 안 + AI 성의 점수 70 이상 + 30자 이상 → 거래가의 10% (보너스 풀에서).
    reserved: 같은 트랜잭션에서 제공자 보너스로 이미 쓰기로 한 풀 토큰. 반환: (금액, 설명)"""
    text_len = len((review.good_text or "").strip()) + len((review.bad_text or "").strip())
    if not on_time:
        return 0, f"완료 후 {REVIEW_DEADLINE_DAYS}일이 지나서 쓴 후기라 환급 대상이 아니에요"
    if quality < REVIEW_REWARD_MIN_QUALITY:
        return 0, f"후기 성의 점수가 {REVIEW_REWARD_MIN_QUALITY}점 미만이에요 ({quality}점)"
    if text_len < REVIEW_REWARD_MIN_CHARS:
        return 0, f"후기가 {REVIEW_REWARD_MIN_CHARS}자 미만이에요 ({text_len}자)"
    amount = max(REVIEW_REWARD_MIN_TOKENS, round(ex.price_tokens * REVIEW_REWARD_RATE))
    left = max(0, _pool_for_update(db).balance - reserved)
    if amount > left:
        return left, f"보너스 풀 잔액이 부족해서 {left}토큰만 돌려드렸어요"
    return amount, f"성의 있는 후기 덕분에 거래가 {ex.price_tokens}토큰의 {int(REVIEW_REWARD_RATE * 100)}%를 돌려드렸어요"


def pay_reviewer_reward(db: Session, ex: Exchange, amount: int) -> None:
    if amount <= 0:
        return
    system = ledger.get_system_user(db)
    ledger.transfer(
        db,
        from_account_id=ledger.get_account(db, system.id, AccountKind.SYSTEM_BONUS_POOL).id,
        to_account_id=ledger.get_account(db, ex.requester_id, AccountKind.AVAILABLE).id,
        amount=amount,
        entry_type=EntryType.REVIEW_REWARD,
        idempotency_key=f"review_reward:{ex.id}",
        exchange_id=ex.id,
        memo="성의 있는 후기 환급",
    )


def lock_provider_account(db: Session, provider_id: int) -> None:
    """같은 제공자에 대한 보너스 계산을 줄 세워요 (하루 상한을 동시에 넘지 않게)."""
    db.scalar(
        select(TokenAccount.id)
        .where(TokenAccount.owner_user_id == provider_id, TokenAccount.kind == AccountKind.AVAILABLE)
        .with_for_update()
    )


def pay(db: Session, ex: Exchange, amount: int) -> None:
    if amount <= 0:
        return
    system = ledger.get_system_user(db)
    ledger.transfer(
        db,
        from_account_id=ledger.get_account(db, system.id, AccountKind.SYSTEM_BONUS_POOL).id,
        to_account_id=ledger.get_account(db, ex.provider_id, AccountKind.AVAILABLE).id,
        amount=amount,
        entry_type=EntryType.REVIEW_BONUS,
        idempotency_key=f"review_bonus:{ex.id}",
        exchange_id=ex.id,
        memo="AI 후기 분석 보너스",
    )
