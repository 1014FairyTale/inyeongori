# 인연고리

경험 속에 숨어 있는 재능을 AI가 찾아 주고, 사람들이 현금 대신 토큰으로 서로의 재능을 나누는 재능 교류 플랫폼입니다.

- 서비스: https://inyeongori.vercel.app
- 시연 영상: https://inyeongori.vercel.app/demo

We:Write 팀 14가 해커톤에서 만든 MVP입니다.

## 왜 만들었나

"저는 잘하는 게 없어요"라고 말하는 사람도 모임 총무, 과외, 행사 준비처럼 남에게 도움이 될 경험을 갖고 있습니다. 다만 그것을 재능이라고 생각하지 못하고, 재능을 나누려 해도 돈이 오가는 서비스는 시작하기가 부담스럽습니다.

인연고리는 세 가지를 합니다.

1. 자기소개와 몇 가지 질문에 대한 답을 읽고 AI가 재능 후보를 근거와 함께 제안합니다. 본인이 맞다고 확인한 것만 재능으로 저장됩니다.
2. 가입하면 100토큰을 받고, 토큰으로만 도움을 주고받습니다. 가격은 재능을 제공하는 사람이 정합니다.
3. "PPT 봐 주세요" 같은 모호한 부탁은 AI가 범위와 분량을 정리해 두 사람이 합의서로 확인한 뒤 거래를 시작합니다. 거래가 끝나면 AI가 후기를 분석해 정성껏 도운 사람에게 보너스 토큰을 줍니다.

## 기능

| 기능 | 화면 | 설명 |
|---|---|---|
| 숨은 재능 찾기 | `/onboarding` | 자기소개와 문답을 바탕으로 AI가 후보, 근거, 확인 질문을 제시하고 사용자가 맞아요·아니에요·수정 중에서 고릅니다 |
| 재능 마켓 | `/market` | 재능을 상품으로 올리고 카테고리와 검색으로 찾습니다 |
| 도와줄 사람 찾기 | `/match` | 필요한 도움을 적으면 재능 일치도, 평점, 활동 이력을 반영해 다섯 명을 추천하고 이유를 함께 보여 줍니다 |
| 부탁 쪼개기, 목표 경로 | `/plans` | 큰 목표를 20~30분짜리 부탁으로 나누거나, 목표까지 받아야 할 도움을 순서대로 설계합니다. 비슷한 상품의 시세로 적정 토큰을 제안합니다 |
| 합의 도우미 | 상품 요청 | 요청 문장을 조건(범위, 분량, 수정 횟수, 시간)으로 정리하고 빠진 조건은 보기를 골라 채웁니다 |
| 토큰 거래 | `/exchanges` | 두 사람이 합의서에 동의하면 토큰을 맡아 두고, 양쪽이 완료를 확인하면 지급합니다. 취소 규칙에 따라 환불합니다 |
| 거래 채팅 | 거래 상세 | 수락된 거래의 두 사람이 일정과 진행 방식을 이야기합니다 |
| 후기와 보너스 | 완료된 거래 | AI가 기여도를 점수와 근거로 판단하고, 금액은 정해진 규칙으로 계산해 제공자에게 지급합니다 |
| 후기 기한과 환급 | 완료된 거래 | 완료 후 7일 안에 구체적인 후기를 쓰면 거래 토큰의 10%를 돌려받습니다. 기한이 지나면 후기를 쓸 때까지 이용이 제한됩니다 |
| 지갑 | `/wallet` | 사용 가능한 토큰, 거래에 묶인 토큰, 거래 내역을 봅니다 |
| 이용 가이드 | `/guide` | 가입 직후 6장짜리 안내를 보여 주고, 홈에서 첫 걸음 다섯 단계를 체크합니다 |

AI가 만든 결과에는 모두 AI 제안이라고 표시하고, 사용자가 고칠 수 있게 했습니다.

## 직접 실행하기

Docker Desktop이 필요합니다.

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python -m seed.seed --reset --yes
```

웹은 http://localhost:3000, API 문서는 http://localhost:8000/docs 에서 열립니다. 마지막 줄은 데모 데이터를 넣는 명령이며 DB를 비우고 다시 채웁니다.

기본 설정(`AI_MOCK=true`)에서는 AI를 부르지 않고 고정된 예시 응답으로 모든 기능이 동작합니다. 실제 AI를 쓰려면 Google AI Studio에서 Gemini API 키를 받아 `.env`의 `GEMINI_API_KEY`를 채우고 `AI_MOCK=false`로 바꾼 뒤 백엔드를 다시 띄웁니다.

```bash
docker compose up -d --force-recreate backend
```

로컬에서는 임베딩 모델 BAAI/bge-m3(약 2GB)를 처음 한 번 내려받습니다. 배포 환경은 Gemini 임베딩을 써서 이미지가 훨씬 작습니다. 자세한 내용은 [배포 가이드](docs/deploy.md)에 있습니다.

테스트는 실제 PostgreSQL에서 돌아갑니다.

```bash
docker compose exec backend pytest
```

## 데모 계정

시드를 넣으면 가상 인물 12명과 시연용 계정이 생깁니다. 로컬 비밀번호는 모두 `demo1234!`이고 `SEED_PASSWORD`로 바꿀 수 있습니다. 운영 사이트는 다른 비밀번호를 씁니다.

| 계정 | 인물 |
|---|---|
| `demo@example.com` | 시연용 요청자 |
| `harin@example.com` | 엑셀요정하린, 엑셀 정산과 행사 예산 |
| `seoyeon@example.com` | 발표장인서연, 발표 리허설과 면접 자기소개 |
| `jiwoo@example.com` | 코딩하는지우, 파이썬 코드와 개발 환경 |
| `doyun@example.com` | 디자인하는도윤, 포스터와 카드뉴스 |

이 밖에 `minjun`, `taehyun`, `yuna`, `hyunwoo`, `sohee`, `jiho`, `yerin`, `gunwoo` 계정이 있습니다. 모두 `@example.com`입니다. 시연 순서는 [데모 시나리오](docs/demo-scenario.md)에 정리했습니다.

## 구조

```
frontend/   Next.js 16 (App Router, TypeScript), Tailwind CSS 4
backend/    FastAPI, SQLAlchemy 2, Alembic, Pydantic v2
  app/      라우터, 서비스(원장, 거래 흐름, 재능 찾기, 매칭, 시세, 보너스), 모델, 스키마
  ai/       공급자 인터페이스, 기능별 프롬프트와 예시 응답, 응답 검증과 재시도
  seed/     데모 데이터
  tests/    pytest 99개
docs/       결정 사항, 데모 시나리오, 배포 가이드
```

DB는 PostgreSQL 16과 pgvector를 씁니다.

토큰은 원장 방식으로 관리합니다. 모든 이동을 기록하고, 잔액이 음수가 되지 않도록 DB 제약과 행 잠금을 걸고, 같은 지급이 두 번 일어나지 않도록 멱등 키를 둡니다. 모든 계정의 잔액을 더하면 항상 0입니다.

AI 호출은 모두 `backend/ai/`의 공급자 인터페이스를 거치므로 LLM이나 임베딩 공급사를 바꿀 수 있습니다. AI는 금액을 직접 정하지 않고 점수와 근거만 내며, 보너스와 환급 금액은 규칙으로 계산합니다.

## 환경변수

| 이름 | 설명 | 기본값 |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | DB 계정 | inyeongori, change-me, inyeongori |
| `DATABASE_URL` | 백엔드 DB 주소. `postgresql://` 형식도 받습니다 | localhost:5432 |
| `TEST_DATABASE_URL` | 테스트용 DB | inyeongori_test |
| `JWT_SECRET` | 로그인 토큰 서명 키. 배포할 때 반드시 바꿉니다 | 없음 |
| `JWT_EXPIRE_MINUTES` | 로그인 유지 시간 | 10080 (7일) |
| `CORS_ORIGINS` | 프론트 주소, 쉼표로 구분 | http://localhost:3000 |
| `AI_MOCK` | true면 AI 대신 고정 응답 | true |
| `LLM_PROVIDER`, `GEMINI_API_KEY`, `LLM_MODEL` | LLM 설정 | gemini, 없음, gemini-3.5-flash-lite |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` | 임베딩 설정. 로컬은 local과 BAAI/bge-m3, 배포는 gemini와 gemini-embedding-001 | local, BAAI/bge-m3, 1024 |
| `INSTALL_EMBEDDINGS` | 빌드 인자. false면 PyTorch 없이 빌드합니다 | true |
| `SEED_PASSWORD` | 시드 계정 비밀번호 | demo1234! |
| `SEED_IF_EMPTY` | 배포 환경에서 사용자가 없을 때만 시드를 넣습니다 | false |
| `SEED_RESET_KEY` | 값을 새로 정하면 서버가 시작할 때 한 번 데이터를 비우고 시드를 다시 넣습니다 | 없음 |
| `NEXT_PUBLIC_API_BASE_URL` | 프론트가 부르는 API 주소 | http://localhost:8000/api/v1 |

## 문서

- [결정 사항](docs/decisions.md): 토큰 정책, 보너스 규칙, 취소와 환불, 화면 원칙 등 만들면서 정한 것들
- [데모 시나리오](docs/demo-scenario.md): 6분 시연 순서
- [배포 가이드](docs/deploy.md): Railway와 Vercel에 올리는 방법
