"""교환 범위 합의 도우미 (기능 6).

모호한 요청 → AI가 분량·범위·수정 횟수·소요 시간으로 정리 → 빠진 조건은 질문으로 채워요.
요청자가 질문에 답하면 같은 API를 answers와 함께 다시 불러요.
AI가 답변을 놓치더라도 답변 내용이 조건에 반드시 반영되도록 서버에서 한 번 더 합쳐요.
"""

import re

from sqlalchemy.orm import Session

from ai.schemas import AgreementDraftAI
from ai.structured import generate
from app.errors import AppError
from app.models import Listing
from app.schemas.market import AgreementTerms
from app.schemas.plan import AgreementDraftIn, AgreementDraftOut, MissingQuestion

FIELD_LABEL = {
    "scope": "범위",
    "quantity": "분량",
    "revisions": "수정 횟수",
    "duration_minutes": "소요 시간",
    "notes": "기타",
}


def _prompt(listing: Listing, req: AgreementDraftIn) -> str:
    lines = [
        "## 재능 상품",
        f"- 제목: {listing.title}",
        f"- 카테고리: {listing.category}",
        f"- 가격: {listing.price_tokens}토큰",
        f"- 예상 소요 시간: {listing.est_minutes}분" if listing.est_minutes else "- 예상 소요 시간: 정보 없음",
        f"- 설명: {listing.description}",
        "",
        "## 요청자가 쓴 요청",
        req.raw_request,
    ]
    if req.previous_terms:
        prev = req.previous_terms.model_dump(exclude_none=True)
        prev.pop("request_text", None)
        if prev:
            lines += ["", "## 지금까지 정리된 조건 (그대로 유지하세요)"]
            lines += [f"- {FIELD_LABEL.get(k, k)}: {v}" for k, v in prev.items()]
    if req.answers:
        lines += ["", "## 앞서 물어본 질문에 대한 요청자의 답변"]
        lines += [f"- {FIELD_LABEL[f]}: {a}" for f, a in req.answers.items()]
    return "\n".join(lines)


def _first_int(text: str) -> int | None:
    m = re.search(r"\d+", text)
    return int(m.group()) if m else None


def _apply_answer(terms: dict[str, object], field: str, answer: str) -> None:
    answer = answer.strip()
    if not answer:
        return
    if field == "revisions":
        n = _first_int(answer)
        if n is None and any(w in answer for w in ("없", "끝", "한 번 보고")):
            n = 0
        if n is not None and terms.get("revisions") is None:
            terms["revisions"] = min(n, 20)
    elif field == "duration_minutes":
        n = _first_int(answer)
        if n is not None and terms.get("duration_minutes") is None:
            terms["duration_minutes"] = n * 60 if "시간" in answer and n < 10 else n
    elif not terms.get(field):
        terms[field] = answer


def draft(db: Session, req: AgreementDraftIn) -> AgreementDraftOut:
    listing = db.get(Listing, req.listing_id)
    if listing is None:
        raise AppError("NOT_FOUND", "재능 상품을 찾을 수 없어요", 404)

    ai = generate("agreement", _prompt(listing, req), AgreementDraftAI)

    terms = ai.terms.model_dump()
    # 이전에 정해진 조건은 AI가 이번에 빠뜨려도 유지해요
    if req.previous_terms:
        for field, value in req.previous_terms.model_dump().items():
            if field != "request_text" and value not in (None, "") and terms.get(field) in (None, ""):
                terms[field] = value
    for field, answer in req.answers.items():
        _apply_answer(terms, field, answer)
    if terms.get("duration_minutes") is not None:
        terms["duration_minutes"] = max(5, min(600, int(terms["duration_minutes"])))  # type: ignore[arg-type]

    answered = set(req.answers)
    missing = [
        MissingQuestion(field=q.field, question=q.question, options=q.options[:4])
        for q in ai.missing
        if q.field not in answered and terms.get(q.field) in (None, "")
    ][:3]

    filled = [
        f"{terms['quantity']}" if terms.get("quantity") else None,
        f"{terms['scope']}" if terms.get("scope") else None,
        f"수정 {terms['revisions']}회" if terms.get("revisions") is not None else None,
        f"{terms['duration_minutes']}분" if terms.get("duration_minutes") is not None else None,
    ]
    summary = ", ".join(x for x in filled if x) or ai.summary

    return AgreementDraftOut(summary=summary, terms=AgreementTerms.model_validate(terms), missing=missing)
