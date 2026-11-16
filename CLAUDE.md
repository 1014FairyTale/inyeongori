# 인연고리 — 작업 가이드 (Claude용)

AI가 숨은 재능을 찾아 주고, 토큰으로 서로의 재능을 나누는 재능 교류 플랫폼. 해커톤 데모용 MVP.

## 작업 방식 (반드시 지킬 것)
1. 단계별로 진행하고, 단계가 끝나면 만든 것 / 실행 방법 / 확인 방법 / 남은 이슈를 보고한 뒤 멈춘다.
2. 기획에 없거나 애매한 결정은 선택지 2~3개와 장단점을 보여 주고 묻는다. 사소한 구현 디테일은 정하고 `docs/decisions.md`에 기록한다.
3. 비밀값은 `.env`로만 관리한다. 코드에 하드코딩 금지. `.env.example`을 같이 갱신한다.
4. 모든 AI 기능은 `AI_MOCK=true`일 때 `backend/ai/mocks/<기능>.json` 고정 응답으로 동작해야 한다.
5. 커밋은 기능 단위로 작게, 메시지는 한국어로.
6. 화면 문구는 한국어, 친근한 존댓말("~해요"). AI 결과에는 항상 "AI 제안" 표시 + 사용자가 수정할 수 있게.

## 기능 단계 (모두 완료)
1. 설계 확인 · 2. 기반 세팅 · 3. 토큰 지갑 + 재능 마켓 + 거래 흐름 · 4. 숨은 재능 발굴 · 5. 합의 도우미 + 부탁 쪼개기 · 6. AI 매칭 + 목표 경로 · 7. 후기 + AI 후기 분석 + 보너스 · 8. 데모 준비(시드·시나리오·배포)

## 기술 스택
- 프론트: Next.js 16 (App Router, TS strict), Tailwind CSS 4 — `frontend/`
  - 주의: Next 16은 학습 데이터와 API가 다를 수 있음. 코드 작성 전 `frontend/node_modules/next/dist/docs/` 확인.
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
docker compose exec -e PYTHONIOENCODING=utf-8 backend python -m seed.seed --reset --yes   # 데모 시드 (DB 전체 초기화!)
cd frontend && npm run lint && npx tsc --noEmit && npm run build   # 프론트 검사
```
- 주의: 이 PC는 Windows 애플리케이션 제어 정책이 SQLAlchemy·argon2의 네이티브 DLL을 차단한다. 백엔드는 로컬 venv가 아니라 Docker 안에서 실행·테스트한다. (로컬은 `py -3 -m compileall`로 문법 검사만 가능)
- API 문서: http://localhost:8000/docs
- Docker Desktop은 사용자 단위로 설치됨: `C:\Users\james\AppData\Local\Programs\DockerDesktop\resources\bin`. 새 터미널이 아니면 PATH에 없을 수 있어서 Claude의 Bash에서는 `export PATH="/c/Users/james/AppData/Local/Programs/DockerDesktop/resources/bin:$PATH"` 후 사용.
- 프론트는 compose 컨테이너로 :3000을 쓴다. 로컬 `npm run dev`와 동시에 띄우면 포트가 충돌한다.

## 코딩 규칙
- 토큰 잔액은 `app/services/ledger.py`의 `transfer()`로만 바꾼다. `balance`를 직접 수정하지 않는다.
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

- `listings.embedding vector(1024)` + embedding_model: 상품 등록·제목/설명/카테고리 수정 시 계산 (`services/embeddings.embed_listing`)
- `plans`(goal, kind breakdown/path, summary), `plan_items`(title, description, minutes, category, suggested_tokens, price_basis market/ai/user, similar_count, linked_listing_id, ai_generated, edited)

## 가격 제안 (D4-1, `services/pricing.py`)
- 활동 텍스트 임베딩 → 내 상품 제외, 활성 상품 중 코사인 유사도 ≥ 기준(`SIMILARITY_THRESHOLD[모델]`) 상위 5개
- 3개 이상이면 가격 중앙값(market), 아니면 AI 추정값(ai), 그것도 없으면 카테고리/전체 중앙값 → 30
- 가장 비슷한 상품은 `linked_listing_id`로 연결해 "○○님에게 요청" 버튼으로 보여 줌

## 합의 도우미 (`services/agreement_helper.py`)
- 저장하지 않는 도우미 API: `POST /ai/agreements/draft {listing_id, raw_request, answers, previous_terms}`
- 프롬프트는 "추측 금지" — 수정 횟수·분량은 말하지 않았으면 null + 질문 (실측에서 '수정 1회'를 지어내던 문제 수정)
- 서버가 답변을 조건에 직접 합치고(숫자 파싱), previous_terms로 이전에 정한 조건을 유지 (AI가 매번 다르게 빠뜨리는 문제 방지)

## AI 매칭 (`services/matching.py`, `POST /match`)
- 요청 임베딩 → user_talents·listings에서 각 50개 → 사람 단위로 최고 유사도
- 후보 필터: 유사도 ≥ (기준 - MATCH_MIN_SIMILARITY_MARGIN), 그리고 ≥ (1등 - MATCH_RELATIVE_CUTOFF)
- 점수 = 0.7×유사도 + 0.2×베이지안 평점/5 + 0.1×log 활동 → 상위 N
- 이유: 상위 N명을 LLM 1회(`match_reason`)로 생성, AI가 relevant=false로 표시한 후보는 제외, 실패 시 템플릿
- `provider_stats()`: 완료 횟수 + `reviews.rating_stats()` 평점
- 공개 프로필 `GET /users/{id}`

## 목표 경로 (`plans.kind = path`)
- 부탁 쪼개기와 같은 테이블·가격 로직 재사용, 단계마다 `why`(왜 필요한지) 추가
- 각 단계: 가장 비슷한 상품 연결("○○님에게 요청") + "맞는 사람 찾기"(/match?q=단계)

## 후기·보너스 (`services/reviews.py`, `services/bonus.py`)
- `reviews`(exchange_id unique, rating 1~5, good_text, bad_text), `review_analyses`(contribution_score, summary, reasons, flags, eligible, base_bonus, final_bonus, adjustments)
- 완료된 거래의 요청자만, 거래당 1회. 저장 → AI 분석(`review_analysis`) → `bonus.decide()` 규칙 → `bonus.pay()` (pool → 제공자, `review_bonus:{exchange_id}`)
- AI는 점수·근거만, 금액은 규칙(D5-A). 모든 계산 단계를 adjustments에 기록.
- 하루 상한 동시성: 제공자 available 계정을 먼저 FOR UPDATE → 같은 제공자 보너스 계산이 줄을 섬. 풀 계정도 FOR UPDATE로 읽음.
- AI 실패 시 후기만 저장, `POST /exchanges/{id}/review/analyze`로 재시도 (이미 분석됐으면 그대로 반환 → 중복 지급 없음)
- 하루 기준은 한국 시간(UTC+9 고정 오프셋, slim 이미지에 tzdata가 없어서)

## 처음 이용 가이드
- `/guide` 슬라이드(내용은 `frontend/app/guide/page.tsx`의 SLIDES). 기능·정책(토큰, 10% 환급, 7일 기한 등)이 바뀌면 슬라이드 문구도 같이 고칠 것
- 가입 후 `/guide?next=...`로 이동, 끝/건너뛰기 시 `POST /auth/me/tutorial` → `users.tutorial_seen_at`
- 첫 걸음 체크리스트: `services/getting_started.py` (MeOut.getting_started), 프론트 `components/GettingStarted.tsx`

## 후기 기한·환급 (`services/review_policy.py`, `bonus.decide_reviewer_reward`)
- 요청자는 완료 후 `REVIEW_DEADLINE_DAYS`(7일) 안에 후기. 기한 안 + AI `review_quality` ≥ 70 + 30자 이상 → 거래가 10% 환급 (`review_reward:{exchange_id}`, 보너스 풀)
- 기한을 넘긴 미작성 후기가 있으면 `CurrentUser` 의존성이 403 `SERVICE_BLOCKED`. 막혀도 열려 있어야 하는 엔드포인트는 `LoggedInUser` 사용 (auth/me, 거래 상세, 후기 쓰기·재분석·조회)
- 새 엔드포인트를 만들 때: 기본은 `CurrentUser`. 막힌 사람도 써야 하면 `LoggedInUser` (`docs/decisions.md`와 맞출 것)
- 막힌 사용자의 상품·재능은 `review_policy.blocked_user_ids()`로 마켓·매칭에서 제외, 요청도 거부
- 프론트: `ReviewGate`(layout)가 마감 배너 / 차단 화면, API가 SERVICE_BLOCKED를 주면 `REFRESH_ME_EVENT`로 내 정보 갱신

## 거래 채팅 (`services/chat.py`, `routers/chat.py`)
- `exchange_messages`(exchange_id, sender_id, kind user/system, body) + `exchanges.requester_last_read_id / provider_last_read_id`
- 상태: open(accepted·cancel_requested·completed) / readonly(수락 후 cancelled) / closed(그 외)
- `GET /exchanges/{id}/messages?after_id=` (가져온 데까지 읽음 처리), `POST .../messages`, `GET /exchanges/unread`
- 주의: chat 라우터는 exchanges 라우터보다 먼저 include (`/exchanges/unread`가 `/exchanges/{id}`에 걸리지 않게)
- 상태 안내는 `exchange_flow.post_system()` — 상태를 바꾸는 함수에서 같은 트랜잭션으로 남긴다

## 임베딩 기준값 (`EMBEDDING_THRESHOLDS`)
- 모델별 price / match / relative / strong. 모델을 바꾸거나 추가하면 반드시 실측해서 넣는다 (관련·무관 쌍 유사도 분포).
- 배포는 `EMBEDDING_PROVIDER=gemini` + `gemini-embedding-001`(1024), 로컬은 bge-m3. 모델이 바뀌면 서버 시작 시 backfill이 다시 임베딩한다.

## 시드·데모
- 대상은 대학생 전용이 아닌 누구나. 화면 문구·AI 프롬프트·시드에 학생·학교·캠퍼스 표현을 쓰지 않는다. 학교·전공 필드는 화면에서 뺐다 (DB 컬럼은 남김)
- 시연 영상 `/demo` (`app/demo`, 파일 `frontend/public/demo/*.mp4`). 포스터 QR이 이 주소를 가리키니 경로를 바꾸지 말 것
- `backend/seed/data.py`(가상 인물), `seed.py`(실제 서비스 함수로 생성, 후기 분석은 SeedLLM으로 고정 점수)
- 데모 대본 `docs/demo-scenario.md`, 배포 가이드 `docs/deploy.md`
- 시드 전에 개발 DB에 사용자가 직접 만든 계정이 있으면 지우기 전에 확인받는다.

## 서버 시작 시
- `warm_up_embeddings()`를 백그라운드 스레드로 실행: 임베딩 모델 미리 로드 + 임베딩이 없거나 모델이 다른 재능·상품 다시 계산. 실패해도 서버는 뜬다.

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
- 주의: Windows 바인드 마운트에서는 frontend 컨테이너의 핫 리로드가 안 된다. 프론트 코드를 바꾼 뒤에는 `docker compose restart frontend` (또는 컨테이너를 멈추고 로컬 `npm run dev`).
- 브라우저 패널 스크린샷이 오른쪽이 잘려 보일 때가 있음 → 레이아웃 판단은 JS로 `scrollWidth`/요소 rect 확인.
- `Field`/`TextArea`의 `className`은 기본 스타일에 '추가'된다 (덮어쓰기 아님). 높이 조절 등에 사용.
- AI 결과 UI 공통 컴포넌트: `AiBadge`(AI 제안 글자 표시), `AiLoading`(문구 순환 로딩), 실패 시 ErrorBox + "다시 시도".

## 디자인 규칙 (개편 후)
- 색 토큰(globals.css): background 크림, foreground, muted, line, brand(주황), danger, success. radius는 전부 0.
- 금지: 둥근 모서리, 색 띠 콜아웃(border-l 강조), 배경색 강조 박스, 그라데이션, 그림자, 이모지·장식 아이콘, 같은 크기 카드 격자, 과장된 라벨.
- 구획 = `Card`(border-t border-foreground) 또는 선으로 구분한 목록(border-b border-line). 뱃지·상태는 색 글자. 채운 배경은 주 버튼(bg-brand)만.
- 로딩은 `PageLoading`/`LogoSpinner`(components/Logo.tsx), AI 로딩은 `AiLoading`. "불러오는 중…" 글자만 쓰지 말 것.

## 결정 사항
`docs/decisions.md`가 기준. 바뀌면 이 파일과 함께 갱신.

## 문서 문체 (README·docs)
- 이모지, 경고 아이콘, 인용 상자 콜아웃(`>`, `[!NOTE]`), 배지, 과장된 라벨을 쓰지 않는다. 굵게도 아낀다.
- 위계는 제목 단계와 문단, 표로만. 사실을 담담하게 쓴다.
