# 인연고리

> AI가 숨은 재능을 찾아 주고, 토큰으로 서로의 재능을 나누는 대학생 재능 교류 플랫폼

현금 없이 토큰으로만 거래해요. "나는 재능이 없다"고 생각하는 학생도 AI의 도움으로 자기 경험 속 재능을 찾고, 요청 범위를 미리 합의해서 갈등 없이 재능을 주고받을 수 있어요.

## 빠른 시작

준비물: [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
cp .env.example .env          # 필요하면 JWT_SECRET, POSTGRES_PASSWORD 변경
docker compose up -d --build
```

- 웹: http://localhost:3000
- API 문서(Swagger): http://localhost:8000/docs
- 테스트: `docker compose exec backend pytest`

AI 키가 없어도 `AI_MOCK=true`(기본값)로 모든 기능이 고정 예시 응답으로 동작해요.

### 실제 AI로 실행하기
1. [Google AI Studio](https://aistudio.google.com)에서 Gemini API 키를 무료로 발급받아요.
2. `.env`에서 `GEMINI_API_KEY=발급받은키`, `AI_MOCK=false`로 바꿔요.
3. `docker compose up -d --force-recreate backend`
4. 처음 재능을 확정할 때 임베딩 모델(bge-m3, 약 2GB)을 내려받아요. 한 번 받으면 `hf_cache` 볼륨에 남아요.

> 백엔드 이미지는 CPU용 PyTorch를 포함해서 약 2.2GB예요. 임베딩 없이 가볍게 빌드하려면
> `docker compose build --build-arg INSTALL_EMBEDDINGS=false backend` (이때는 `AI_MOCK=true`로 실행)

## 환경변수

| 이름 | 설명 | 기본값 |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | DB 계정 | inyeongori / change-me / inyeongori |
| `DATABASE_URL` | 백엔드 DB 주소 (compose 안에서는 자동 설정) | localhost:5432 |
| `TEST_DATABASE_URL` | pytest용 DB | …/inyeongori_test |
| `JWT_SECRET` | JWT 서명 키 (**배포 시 반드시 변경**) | — |
| `JWT_EXPIRE_MINUTES` | 로그인 유지 시간 | 10080 (7일) |
| `CORS_ORIGINS` | 프론트 주소 (쉼표 구분) | http://localhost:3000 |
| `AI_MOCK` | true면 AI 호출 대신 고정 응답 | true |
| `LLM_PROVIDER` / `GEMINI_API_KEY` / `LLM_MODEL` | LLM 설정 (Google AI Studio 무료 키) | gemini / — / gemini-flash-latest |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `EMBEDDING_DIM` | 임베딩 설정 | local / BAAI/bge-m3 / 1024 |
| `NEXT_PUBLIC_API_BASE_URL` | 프론트가 부르는 API 주소 | http://localhost:8000/api/v1 |

## 기능 소개

| 기능 | 상태 |
|---|---|
| 회원가입·로그인, 가입 보너스 100토큰 | ✅ 2단계 |
| 토큰 지갑 (원장 기반, 보류·지급·환불) | ✅ 3단계 |
| 재능 마켓 + 거래 흐름 (합의서 동의 → 보류 → 완료 → 지급 / 취소 → 환불) | ✅ 3단계 |
| 숨은 재능 발굴 (AI 후보 + 근거 + 확인 질문 → 맞아요/아니에요/수정 → 임베딩 저장) | ✅ 4단계 |
| 교환 범위 합의 도우미, 부탁 쪼개기 | 5단계 |
| AI 매칭, 목표 기반 교환 경로 | 6단계 |
| 후기 + AI 후기 분석 + 보너스 토큰 | 7단계 |

## 스크린샷

_(8단계에서 추가)_

## 결정 사항

| # | 항목 | 결정 | 이유 |
|---|---|---|---|
| D1 | LLM | Gemini API 무료 등급 | 비용 0. 무료 등급은 입력이 Google 서비스 개선에 쓰일 수 있으니 데모는 가상 데이터로만 진행 |
| D2 | 임베딩 | 로컬 `BAAI/bge-m3`, 1024차원 | 무료, 키 불필요, 한국어 강함. 첫 실행 시 약 2GB 모델 다운로드 |
| D3 | 매칭 설명 | 상위 N명 설명을 LLM 1회 호출로 생성, 실패·mock이면 템플릿 | 비용·속도 균형 |
| D4 | 토큰 개념 | **토큰 = 가격.** 제공자가 상품 가격을 정하고 시간과 무관. 좋은 후기 + AI 판단 시 가격보다 더 받음(보너스) | 기획자 결정 |
| D4-1 | 부탁 쪼개기 적정 토큰 | 임베딩으로 비슷한 상품을 찾아 가격 중앙값 제안. 비슷한 상품이 3개 미만이면 AI가 마켓 가격대를 참고해 추정 ("AI 제안" 표시) | 시세 기반이라 근거가 분명함 |
| D5 | 후기 보너스 | 기여도 70점 이상 + 별점 4 이상 + 후기 20자 이상일 때 지급. 70~84점은 거래가의 10%, 85점 이상은 20%, 최소 1·**거래당 최대 10토큰**, 제공자당 하루 최대 30토큰. 같은 두 사람의 30일 내 2번째 거래는 50%, 3번째부터 0. 시스템 보너스 풀(초기 100,000)에서 지급. AI는 점수와 근거를 내고, 금액은 규칙으로 계산 | 남용 방지 |
| D6 | 취소·환불 | 수락 전에는 누구나 취소(토큰 이동 없음). 수락 후 제공자 취소는 즉시 전액 환불, 요청자 취소는 제공자 동의가 필요 | 도움받고 취소해 환불받는 악용 방지 |
| D7 | JWT 보관 | localStorage + Authorization 헤더 | 프론트(Vercel)·백엔드(Railway) 도메인이 달라도 설정이 단순 |
| D8 | 프로젝트 위치 | `C:\Users\james\hackathon\inyeongori` (OneDrive 밖) | node_modules 동기화·파일 잠금 문제 회피 |
| — | 원장 구조 | 계정 테이블(`token_accounts`, 캐시 잔액 + CHECK ≥ 0) + 이동 기록(`ledger_transfers`, from→to). 행 잠금은 id 순서 `FOR UPDATE`, 멱등 키 unique | 잔액 정합성·동시성·중복 방지 |
| — | 토큰 발행 | 시스템 계정의 `system_issuance`가 음수로 발행. 전체 잔액 합은 항상 0 | 토큰이 어디서 생겼는지 추적 가능 |
| — | DB 세션 | SQLAlchemy 동기 세션 (FastAPI 스레드풀) | 행 잠금·테스트가 단순 |
| — | 패키지 관리 | 백엔드 pip + pyproject, 프론트 npm | 이 PC에 uv·pnpm이 없음, 추가 설치 불필요 |
| — | 비밀번호 해시 | argon2 | 현재 권장 알고리즘 |
| — | 가입 보너스 | 100토큰, 시스템 발행 계정에서 지급 (가입과 같은 트랜잭션) | 기획 |
| — | 개발 실행 환경 | 백엔드는 Docker 안에서만 실행·테스트 | 이 PC의 Windows 애플리케이션 제어 정책이 일부 Python 네이티브 DLL을 차단 |
| — | 상품 가격 범위 | 1~500토큰. 예상 소요 시간은 참고 정보일 뿐 가격 계산에 쓰지 않음 | D4 (토큰 = 가격) |
| — | 카테고리 | 학업·과제, 발표·PPT, 디자인, 개발·IT, 엑셀·문서, 어학, 음악·예술, 운동·게임, 진로·취업, 생활·기타 (10개, `constants.py`) | 대학생 재능 범위를 넓게 덮음 |
| — | 거래 시작 시점 | 요청을 보내면 요청자가 합의서 v1에 동의한 상태. 제공자가 동의(=수락)하는 순간 토큰 보류. 조건을 바꾸면 새 버전이 생기고 상대가 다시 동의해야 함 | 기능 6 "양측 확인 후 거래 시작" |
| — | 잔액 확인 시점 | 요청할 때 잔액을 안내용으로 확인하고, 수락할 때 행 잠금과 함께 다시 확인. 그사이 잔액이 줄면 수락이 거부됨 | 여러 요청을 동시에 보내도 음수 불가 |
| — | 수락 후 조건 변경 | 불가 (취소 후 다시 요청) | 보류된 금액과 합의 내용이 어긋나지 않게 |
| — | 남의 거래 조회 | 404로 응답 (존재 여부도 숨김) | 개인정보 |
| — | 하단 탭 내비게이션 | 홈·마켓·거래·지갑 | 모바일 우선 |
| — | 재능 후보 수 | AI가 3~5개 제안 (스키마상 1~6개 허용) | 확인 부담이 적으면서 고를 거리가 있는 수 |
| — | AI 후보 저장 방식 | 후보는 모두 기록하고, 확정한 것만 `user_talents`에 저장. 수정하면 AI 원래 제안은 남기고 최종 값만 재능에 저장 | "AI 추론은 확정이 아니다" 원칙 + 나중에 AI 품질 확인용 |
| — | 확정 후 되돌리기 | '빼기'로 재능에서 제거 가능, '다시 넣기'로 복구 | 실수 방지 |
| — | 카테고리 밖 응답 | AI가 목록에 없는 카테고리를 주면 '생활·기타'로 저장 | 실패 대신 안전하게 처리 |
| — | 임베딩 실패 | 재능 저장은 진행하고 임베딩만 비워 둔 뒤 나중에 채움 | 임베딩 서버 문제로 온보딩이 막히지 않게 |
| — | 임베딩 텍스트 | "재능 이름 (카테고리): 설명" | 매칭 시 요청 문장과 비교하기 좋은 형태 |
| — | AI 실패 응답 | 502 `AI_FAILED` + 한국어 메시지, 화면에 "다시 시도" | 기획의 UI 가이드 |
| — | 자기소개 → 프로필 | 처음 재능 찾기에 쓴 자기소개를 프로필 소개(bio)로 저장 (비어 있을 때만) | 입력 반복 줄이기 |
| — | UI | Tailwind만 사용 (shadcn/ui는 필요해지면 도입), 시스템 한글 폰트 | 빌드 시 외부 폰트 다운로드 없음 |
