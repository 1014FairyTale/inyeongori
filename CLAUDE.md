# 인연고리 — 작업 가이드 (Claude용)

AI가 숨은 재능을 찾아 주고, 토큰으로 서로의 재능을 나누는 **대학생 재능 교류 플랫폼**. 해커톤 데모용 MVP.

## 작업 방식 (반드시 지킬 것)
1. 단계별로 진행하고, 단계가 끝나면 **만든 것 / 실행 방법 / 확인 방법 / 남은 이슈**를 보고한 뒤 멈춘다.
2. 기획에 없거나 애매한 결정은 선택지 2~3개와 장단점을 보여 주고 묻는다. 사소한 구현 디테일은 정하고 README "결정 사항"에 기록한다.
3. 비밀값은 `.env`로만 관리한다. 코드에 하드코딩 금지. `.env.example`을 같이 갱신한다.
4. 모든 AI 기능은 `AI_MOCK=true`일 때 `backend/ai/mocks/<기능>.json` 고정 응답으로 동작해야 한다.
5. 커밋은 기능 단위로 작게, 메시지는 한국어로.
6. 화면 문구는 한국어, 친근한 존댓말("~해요"). AI 결과에는 항상 "AI 제안" 표시 + 사용자가 수정할 수 있게.

## 핵심 기능 (단계)
1. 설계 확인 ✅ · 2. 기반 세팅 ✅ · 3. 토큰 지갑 + 재능 마켓 + 거래 흐름 ✅ · 4. 숨은 재능 발굴 ✅ · 5. 합의 도우미 + 부탁 쪼개기 · 6. AI 매칭 + 목표 경로 · 7. 후기 + AI 후기 분석 + 보너스 · 8. 데모 준비(시드·시나리오·배포)

## 기술 스택
- 프론트: Next.js 16 (App Router, TS strict), Tailwind CSS 4 — `frontend/`
  - ⚠️ Next 16은 학습 데이터와 API가 다를 수 있음. 코드 작성 전 `frontend/node_modules/next/dist/docs/` 확인.
- 백엔드: FastAPI, SQLAlchemy 2 (동기 세션), Alembic, Pydantic v2 — `backend/`
- DB: PostgreSQL 16 + pgvector (`pgvector/pgvector:pg16` 이미지)
- AI: LLM = Gemini API 무료 등급 (Google AI Studio), 임베딩 = 로컬 `BAAI/bge-m3` (1024차원)
  - 호출은 반드시 `backend/ai/` provider 인터페이스(`ai/providers/base.py`)를 통해서만.
  - 프롬프트는 `backend/ai/prompts/<기능>.md`, LLM 출력은 Pydantic으로 검증, 실패 시 1회 재시도.
- 인증: 이메일+비밀번호(argon2) + JWT(Bearer, 프론트는 localStorage 보관)

## 실행 명령어
```bash
cp .env.example .env                 # 처음 한 번
docker compose up -d --build         # db + backend(:8000) + frontend(:3000)
docker compose exec backend pytest   # 백엔드 테스트 (inyeongori_test DB 사용)
docker compose exec backend alembic revision -m "설명"   # 마이그레이션 생성 (수동 작성)
cd frontend && npm run lint && npx tsc --noEmit && npm run build   # 프론트 검사
```
- ⚠️ 이 PC는 Windows 애플리케이션 제어 정책이 SQLAlchemy·argon2의 네이티브 DLL을 차단한다. **백엔드는 로컬 venv가 아니라 Docker 안에서 실행·테스트**한다. (로컬은 `py -3 -m compileall`로 문법 검사만 가능)
- API 문서: http://localhost:8000/docs
- Docker Desktop은 사용자 단위로 설치됨: `C:\Users\james\AppData\Local\Programs\DockerDesktop\resources\bin`. 새 터미널이 아니면 PATH에 없을 수 있어서 Claude의 Bash에서는 `export PATH="/c/Users/james/AppData/Local/Programs/DockerDesktop/resources/bin:$PATH"` 후 사용.
- 프론트는 compose 컨테이너로 :3000을 쓴다. 로컬 `npm run dev`와 동시에 띄우면 포트가 충돌한다.

## 코딩 규칙
- **토큰 잔액은 `app/services/ledger.py`의 `transfer()`로만 바꾼다.** `balance`를 직접 수정하지 않는다.
  - `transfer()`는 커밋하지 않는다(호출자 트랜잭션에 포함). 계정 행은 id 순서로 `FOR UPDATE`.
  - 모든 이동에 의미 있는 `idempotency_key`를 준다 (예: `signup:{user_id}`, `escrow:{exchange_id}`, `payout:{exchange_id}`).
- 커밋은 라우터(유스케이스 끝)에서 `db.commit()`. 서비스는 커밋하지 않는다.
- 에러는 `app.errors.AppError(code, message, status)`로 던진다 → `{"error": {"code", "message", "details"}}`.
- 정책 수치는 `app/core/constants.py`에만 둔다.
- 토큰·거래 로직을 바꾸면 pytest(특히 잔액 음수 방지·중복 완료·동시성)를 같이 추가한다. 테스트는 실제 Postgres에서 돈다.
- 프론트 API 호출은 `lib/api.ts`의 `api()`를 쓰고, 타입은 백엔드 스키마와 맞춘다.

## 데이터 모델 요약 (현재까지)
- `users` (is_system: 시스템 계정 "인연고리", is_admin)
- `token_accounts`: 사용자당 `available`/`escrow`, 시스템은 `system_issuance`(음수 허용 — 발행)/`system_bonus_pool`. `balance >= 0` CHECK.
- `ledger_transfers`: from→to, amount>0, entry_type(system_funding/signup_bonus/escrow_hold/payout/refund/review_bonus/cert_bonus), exchange_id, idempotency_key(unique)
- 불변식: 모든 계정 balance 합 = 0, 각 계정 balance = 원장 재계산 값
- `listings`: provider_id, title, description, category(`LISTING_CATEGORIES`), price_tokens(1~500, 가격 = 시간과 무관), est_minutes(참고용), status(active/paused)
- `exchanges`: listing_id, requester_id, provider_id, price_tokens(요청 시점 스냅샷), status, requester_done_at/provider_done_at, cancel_requested_by, cancelled_by
  - 상태 머신은 `app/services/exchange_flow.py` (상단 주석에 흐름도). 상태 변경 전 거래 행 `FOR UPDATE`.
  - requested →(양측이 현재 합의서에 동의)→ accepted[보류 escrow:{id}] →(양측 완료)→ completed[지급 payout:{id}]
  - 수락 후 제공자 취소 = 즉시 환불(refund:{id}), 요청자 취소 = cancel_requested → 제공자 승인 시 환불 / 거절 시 accepted
- `agreements`: exchange_id, version, proposed_by, terms(JSONB: request_text/scope/quantity/revisions/duration_minutes/notes), ai_generated, requester_agreed_at, provider_agreed_at
  - 조건 수정 = 새 version, 제안자만 동의한 상태로 시작. 수락 후에는 수정 불가.

- `discovery_sessions`(자기소개·문답·격려 문구), `talent_candidates`(AI 후보: name/category/evidence/source_quote/confirm_question/description, status pending/accepted/edited/rejected, talent_id), `user_talents`(확정 재능 + `embedding vector(1024)` + embedding_model)
  - 확정(맞아요/수정)한 것만 user_talents에 저장. 후보의 AI 원래 제안은 남기고, 수정한 값은 talent에 저장 (`final_name`으로 응답).
  - 임베딩 실패해도 재능 저장은 진행 (embedding=NULL) → `discovery.backfill_embeddings()`로 채움. embedding_model이 현재 모델과 다르면 다시 임베딩 대상.

## AI 모듈 규칙
- 호출 흐름: `ai/structured.generate(feature, user_text, PydanticSchema)` → provider.generate_json → `model_validate_json` → 실패 시 1회 재시도 → `AIError` → API는 502 `AI_FAILED`.
- 새 AI 기능 추가 시: `ai/schemas.py`에 출력 스키마, `ai/prompts/<feature>.md`, `ai/mocks/<feature>.json` 세 개를 같이 만든다.
- Gemini: `google-genai` SDK, `response_json_schema`에 Pydantic `model_json_schema()` 전달, 429는 "무료 한도 초과" 메시지.
- 임베딩: `sentence-transformers` + `BAAI/bge-m3` (CPU torch). 모델은 `hf_cache` 볼륨에 캐시. mock 모드는 n-gram 해싱 임베딩.
- 테스트에서 LLM 바꾸기: `monkeypatch.setattr(ai.structured, "get_llm", lambda: FakeLLM([...]))`.

## 프론트 메모
- Next 16 + Cache Components: `useParams`/`usePathname`/`useSearchParams`를 쓰는 클라이언트 컴포넌트는 `<Suspense>`로 감싸야 빌드된다.
- 로컬에서 `npm run build`를 하면 `frontend/.next`가 생겨 컨테이너 개발 서버와 섞인다. 빌드 확인 후 `rm -rf frontend/.next` 하고 `docker compose restart frontend`.
- 로그인 복원 실패 시 401일 때만 토큰을 지운다 (서버 재시작 중 로그아웃 방지).
- ⚠️ Windows 바인드 마운트에서는 frontend 컨테이너의 핫 리로드가 안 된다. 프론트 코드를 바꾼 뒤에는 `docker compose restart frontend` (또는 컨테이너를 멈추고 로컬 `npm run dev`).
- 브라우저 패널 스크린샷이 오른쪽이 잘려 보일 때가 있음 → 레이아웃 판단은 JS로 `scrollWidth`/요소 rect 확인.
- AI 결과 UI 공통 컴포넌트: `AiBadge`(✨ AI 제안), `AiLoading`(문구 순환 로딩), 실패 시 ErrorBox + "다시 시도".

## 결정 사항
README.md의 "결정 사항" 섹션이 기준. 바뀌면 둘 다 갱신.
