# 배포 가이드 (Railway + Vercel)

구성: **Railway** = 백엔드(FastAPI) + PostgreSQL(pgvector), **Vercel** = 프론트(Next.js)

> 배포 환경에서는 임베딩을 로컬 bge-m3 대신 **Gemini 임베딩 API**로 써요 (결정 사항 참고).
> 이미지가 약 2.2GB → 수백 MB로 줄고, 서버 메모리도 적게 들어요. 같은 1024차원이라 DB 구조는 같아요.

계정 만들기·로그인·결제 정보 입력은 직접 해 주세요. 아래 순서대로 하면 30분 정도 걸려요.

---

## 1. GitHub에 올리기
Railway와 Vercel은 GitHub 저장소에서 코드를 가져가요.
1. GitHub에서 새 저장소를 만들어요 (Private 추천).
2. 프로젝트 폴더에서:
   ```bash
   git remote add origin https://github.com/<내 계정>/inyeongori.git
   git push -u origin main
   ```
   - 커밋에 들어간 이메일이 공개돼요. 숨기려면 GitHub 설정의 noreply 주소로 바꾼 뒤 올리세요.
   - `.env`는 올라가지 않아요 (`.gitignore`에 포함).

## 2. Railway: 데이터베이스
1. https://railway.com → New Project → **Deploy a template** → `pgvector` 검색 → PostgreSQL + pgvector 템플릿 선택
   - 일반 PostgreSQL에는 pgvector 확장이 없을 수 있어요. 마이그레이션이 `CREATE EXTENSION vector`를 실행하니 꼭 pgvector가 있는 DB여야 해요.
2. 만들어지면 DB 서비스의 **Variables**에서 `DATABASE_URL`이 보이는지 확인해요.

## 3. Railway: 백엔드
1. 같은 프로젝트에서 **New → GitHub Repo** → 이 저장소 선택
2. 서비스 **Settings**
   - Root Directory: `backend`
   - (railway.json 덕분에 Dockerfile 빌드·헬스체크가 자동 설정돼요)
3. 서비스 **Variables**에 아래를 넣어요

   | 이름 | 값 |
   |---|---|
   | `DATABASE_URL` | `${{ Postgres.DATABASE_URL }}` (DB 서비스 이름에 맞게. 자동 변환돼요) |
   | `JWT_SECRET` | 긴 랜덤 문자열 (`py -c "import secrets; print(secrets.token_urlsafe(48))"`) |
   | `CORS_ORIGINS` | Vercel 주소 (4단계 후에 채워요. 예: `https://inyeongori.vercel.app`) |
   | `AI_MOCK` | `false` (키 없이 시연하려면 `true`) |
   | `GEMINI_API_KEY` | AI Studio 키 |
   | `LLM_MODEL` | `gemini-3.5-flash-lite` |
   | `EMBEDDING_PROVIDER` | `gemini` |
   | `EMBEDDING_MODEL` | `gemini-embedding-001` |
   | `EMBEDDING_DIM` | `1024` |
   | `INSTALL_EMBEDDINGS` | `false` (빌드 인자: PyTorch를 설치하지 않아요) |
   | `SEED_PASSWORD` | 데모 계정 비밀번호 (공개 배포라면 기본값 말고 새로 정하세요) |

4. **Settings → Networking → Generate Domain**으로 주소를 만들어요 (예: `https://inyeongori-backend.up.railway.app`).
5. 배포가 끝나면 `https://<백엔드 주소>/api/v1/health` 가 `{"status":"ok", ...}` 를 돌려주는지 확인해요.
6. 시드 데이터 넣기: Variables에 `SEED_IF_EMPTY` = `true`를 추가하면, 서버가 켜질 때 **DB에 사용자가 없을 때만** 데모 시드를 넣어요 (약 30초, 백그라운드).
   - 이미 사용자가 있으면 아무것도 하지 않아요. 처음부터 다시 넣고 싶으면 CLI(`railway run python -m seed.seed --reset --yes`)를 써요.
   - 시드 계정 비밀번호는 `SEED_PASSWORD` 값이에요.

## 4. Vercel: 프론트엔드
1. https://vercel.com → Add New → Project → 이 저장소 Import
2. **Root Directory**: `frontend` (Framework는 Next.js로 자동 인식)
3. **Environment Variables**: `NEXT_PUBLIC_API_BASE_URL` = `https://<백엔드 주소>/api/v1`
4. Deploy → 나온 주소(예: `https://inyeongori.vercel.app`)를 Railway 백엔드의 `CORS_ORIGINS`에 넣고 백엔드를 다시 배포해요.

## 5. 확인
- Vercel 주소 접속 → 가입 → 100토큰 → "AI가 내 재능 찾아 주기"
- 브라우저 개발자 도구에 CORS 에러가 나면 `CORS_ORIGINS` 값(끝에 `/` 없이)을 확인해요.

## 비용·제한 메모
- Gemini 무료 등급은 분당 호출 수 제한이 있어요. 시연 중 연속으로 많이 누르면 "AI 무료 사용 한도를 넘었어요"가 나올 수 있어요 → 잠시 후 다시 시도.
- Railway는 사용량 기반 과금이에요. 시연이 끝나면 서비스를 멈춰 두면 비용이 거의 안 나와요.
- 시연 직전에 AI가 불안하면 `AI_MOCK=true`로 바꾸면 고정 예시로 모든 기능이 돌아가요 (임베딩도 mock으로 바뀌니 시드를 다시 넣어야 매칭이 맞아요).
