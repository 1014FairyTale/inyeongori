"""데모 시드 데이터 넣기.

    docker compose exec backend python -m seed.seed --reset

- --reset: 모든 데이터를 지우고 새로 만들어요 (개발·데모 DB 전용!).
- 비밀번호는 SEED_PASSWORD 환경변수 (기본값 README '데모 계정' 참고).
- 실제 서비스 로직(가입 → 상품 등록 → 요청 → 수락 → 완료 → 후기 → 보너스)을 그대로 거쳐서 만들기 때문에
  토큰 원장이 항상 정합성을 유지해요.
- 후기 분석은 시드에 적어 둔 점수를 쓰고(LLM 호출 없음), 임베딩은 현재 설정(.env)의 모델을 써요.
"""

import argparse
import json
import os
import sys
from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

import ai.structured
from app.core.constants import BONUS_POOL_INITIAL_TOKENS
from app.db import SessionLocal, engine
from app.models import Listing, TalentSource, User, UserTalent
from app.schemas.auth import SignupRequest
from app.schemas.market import AgreementTerms
from app.services import auth, exchange_flow, reviews
from app.services.discovery import embed_talent
from app.services.embeddings import embed_listing
from app.services.ledger import ensure_system_accounts
from seed.data import COMPLETED, DEMO_REQUESTER, IN_PROGRESS, STUDENTS

DEFAULT_PASSWORD = "demo1234!"
TABLES = (
    "exchange_messages, review_analyses, reviews, plan_items, plans, talent_candidates, user_talents, discovery_sessions, "
    "ledger_transfers, agreements, exchanges, listings, token_accounts, users"
)


class SeedLLM:
    """시드용: 후기 분석은 미리 정해 둔 결과를 돌려주고, 그 밖의 호출은 원래 LLM에 넘겨요.
    (서버가 켜진 상태에서 시드가 돌 때 다른 사용자의 AI 요청이 영향을 받지 않게)"""

    name = "seed"

    def __init__(self, fallback: Callable[[], Any]) -> None:
        self.queue: list[dict[str, Any]] = []
        self._fallback = fallback

    def generate_json(self, *, feature: str, **kwargs: Any) -> str:
        if feature == "review_analysis" and self.queue:
            return json.dumps(self.queue.pop(0), ensure_ascii=False)
        return self._fallback().generate_json(feature=feature, **kwargs)


def email(handle: str) -> str:
    return f"{handle}@example.com"  # example.com은 예시용으로 예약된 도메인이에요


def reset(db: Session) -> None:
    db.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    db.commit()


def make_user(db: Session, password: str, nick: str, handle: str, school: str, major: str, bio: str) -> User:
    user = auth.signup(db, SignupRequest(email=email(handle), password=password, nickname=nick, school=school, major=major))
    user.bio = bio
    return user


def run(db: Session, password: str) -> dict[str, int]:
    ensure_system_accounts(db, BONUS_POOL_INITIAL_TOKENS)
    users: dict[str, User] = {}
    listings: dict[str, Listing] = {}

    for nick, handle, school, major, bio, talents, items in STUDENTS:
        u = make_user(db, password, nick, handle, school, major, bio)
        users[handle] = u
        for name, cat, desc, by_ai in talents:
            t = UserTalent(
                user_id=u.id,
                name=name,
                category=cat,
                description=desc,
                source=TalentSource.AI_CONFIRMED if by_ai else TalentSource.MANUAL,
            )
            db.add(t)
            db.flush()
            embed_talent(t)
        for title, desc, cat, price, minutes in items:
            listing = Listing(provider_id=u.id, title=title, description=desc, category=cat, price_tokens=price, est_minutes=minutes)
            db.add(listing)
            db.flush()
            embed_listing(listing)
            listings[title] = listing
    nick, handle, school, major, bio = DEMO_REQUESTER
    users[handle] = make_user(db, password, nick, handle, school, major, bio)
    db.commit()
    print(f"  학생 {len(STUDENTS)}명 + 데모 계정 1명, 상품 {len(listings)}개")

    original_get_llm = ai.structured.get_llm
    llm = SeedLLM(original_get_llm)
    ai.structured.get_llm = lambda: llm  # type: ignore[assignment]
    try:
        _trades(db, users, listings, llm)
    finally:
        ai.structured.get_llm = original_get_llm  # type: ignore[assignment]
    return {"users": len(users), "listings": len(listings), "completed": len(COMPLETED)}


def _trades(db: Session, users: dict[str, User], listings: dict[str, Listing], llm: SeedLLM) -> None:
    for req, prov, title, request_text, rating, good, bad, score, reasons in COMPLETED:
        requester, provider, listing = users[req], users[prov], listings[title]
        terms = AgreementTerms(request_text=request_text, duration_minutes=listing.est_minutes)
        ex = exchange_flow.create_request(db, requester, listing.id, terms)
        exchange_flow.agree(db, provider, ex.id)
        exchange_flow.complete(db, requester, ex.id)
        exchange_flow.complete(db, provider, ex.id)
        db.commit()
        review = reviews.create_review(db, requester, ex.id, rating, good, bad or None)
        quality = 85 if len(good) + len(bad or "") >= 30 else 45  # 시드: 구체적인 후기는 성의 점수 높게
        llm.queue.append({"contribution_score": score, "summary": reasons[0], "reasons": reasons, "flags": [],
                          "review_quality": quality, "review_quality_reason": "받은 도움을 구체적으로 적었어요." if quality >= 70 else "내용이 짧아 참고하기 어려워요."})
        analysis = reviews.analyze(db, review)
        db.commit()
        bonus = analysis.final_bonus if analysis else 0
        print(f"  거래 완료: {requester.nickname} → {provider.nickname} '{title}' ★{rating} 기여도 {score} 보너스 +{bonus}")

    for req, prov, title, request_text, accept in IN_PROGRESS:
        requester, provider, listing = users[req], users[prov], listings[title]
        ex = exchange_flow.create_request(db, requester, listing.id, AgreementTerms(request_text=request_text))
        if accept:
            exchange_flow.agree(db, provider, ex.id)
        db.commit()
    print(f"  진행 중인 거래 {len(IN_PROGRESS)}건")


def seed_if_empty() -> bool:
    """사용자가 한 명도 없을 때만 시드를 넣어요 (배포 환경의 SEED_IF_EMPTY=true). 넣었으면 True."""
    with SessionLocal() as db:
        if db.query(User).filter(User.is_system.is_(False)).first() is not None:
            return False
        run(db, os.environ.get("SEED_PASSWORD") or DEFAULT_PASSWORD)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="인연고리 데모 시드 데이터")
    parser.add_argument("--reset", action="store_true", help="기존 데이터를 모두 지우고 새로 만들어요")
    parser.add_argument("--yes", action="store_true", help="확인 없이 진행")
    args = parser.parse_args()

    password = os.environ.get("SEED_PASSWORD") or DEFAULT_PASSWORD  # 비어 있으면 기본값
    print(f"DB: {engine.url.render_as_string(hide_password=True)}")
    with SessionLocal() as db:
        if args.reset:
            if not args.yes:
                answer = input("모든 데이터를 지우고 시드를 넣을까요? (yes 입력) ")
                if answer.strip() != "yes":
                    print("취소했어요.")
                    sys.exit(1)
            reset(db)
            print("기존 데이터를 지웠어요.")
        elif db.query(User).filter(User.email == email("harin")).first():
            print("이미 시드가 들어가 있어요. 다시 넣으려면 --reset 을 붙여 주세요.")
            sys.exit(1)
        result = run(db, password)
    print(f"완료: {result}")


if __name__ == "__main__":
    main()
