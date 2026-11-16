# 배포 가이드

백엔드(FastAPI)와 PostgreSQL(pgvector)은 Railway에, 프론트(Next.js)는 Vercel에 올립니다. 순서대로 하면 30분 정도 걸립니다. 계정 만들기, 로그인, 결제 정보 입력은 직접 합니다.

배포 환경에서는 임베딩을 로컬 bge-m3 대신 Gemini 임베딩 API로 계산합니다. 백엔드 이미지가 약 2.2GB에서 380MB로 줄고 메모리도 적게 씁니다. 둘 다 1024차원이라 DB 구조는 같습니다. 이유는 [결정 사항](decisions.md)의 D2-1에 있습니다.

## 1. GitHub에 올리기

Railway와 Vercel은 GitHub 저장소에서 코드를 가져갑니다.

```bash
git remote add origin https://github.com/<계정>/inyeongori.git
git push -u origin main
```

`.env`와 `.env.railway`는 `.gitignore`에 들어 있어 올라가지 않습니다. 커밋 작성자 이메일은 공개 저장소에서 누구나 볼 수 있으니, 숨기려면 GitHub의 noreply 주소로 바꾼 뒤 올립니다.

## 2. Railway 데이터베이스

1. Railway에서 New Project, Deploy a template을 고르고 `pgvector`로 검색해 PostgreSQL과 pgvector가 함께 있는 템플릿을 고릅니다. 마이그레이션이 `CREATE EXTENSION vector`를 실행하므로 pgvector가 없는 일반 PostgreSQL로는 동작하지 않습니다.
2. DB 서비스의 Variables에 `DATABASE_URL`이 있는지 확인합니다.

## 3. Railway 백엔드

1. 같은 프로젝트에서 New, GitHub Repo를 고르고 이 저장소를 연결합니다. 목록에 저장소가 없으면 Configure GitHub App에서 접근을 허용한 뒤 새로고침합니다.
2. 서비스 Settings에서 Root Directory를 `backend`로 정합니다. Dockerfile 빌드와 헬스 체크는 `railway.json`이 설정합니다.
3. 서비스 Variables에 아래 값을 넣습니다.

| 이름 | 값 |
|---|---|
| `DATABASE_URL` | `${{ pgvector.DATABASE_URL }}`. DB 서비스 이름에 맞춥니다 |
| `JWT_SECRET` | 긴 임의 문자열. 예: `py -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | Vercel 주소. 4단계를 마친 뒤 채웁니다 |
| `AI_MOCK` | `false`. 키 없이 시연하려면 `true` |
| `GEMINI_API_KEY` | AI Studio에서 받은 키 |
| `LLM_MODEL` | `gemini-3.5-flash-lite` |
| `EMBEDDING_PROVIDER` | `gemini` |
| `EMBEDDING_MODEL` | `gemini-embedding-001` |
| `EMBEDDING_DIM` | `1024` |
| `INSTALL_EMBEDDINGS` | `false`. PyTorch를 설치하지 않습니다 |
| `SEED_PASSWORD` | 데모 계정 비밀번호. 기본값 대신 새로 정합니다 |
| `PORT` | `8000` |

4. Settings, Networking, Generate Domain에서 포트 8000으로 주소를 만듭니다.
5. 배포가 끝나면 `https://<백엔드 주소>/api/v1/health`가 `{"status":"ok", ...}`를 돌려주는지 확인합니다.

### 데모 데이터

- `SEED_IF_EMPTY=true`를 넣으면 서버가 켜질 때 사용자가 한 명도 없을 때만 시드를 넣습니다. 30초쯤 걸립니다.
- 이미 데이터가 있는 상태에서 처음부터 다시 넣으려면 `SEED_RESET_KEY`에 새 값(예: 날짜)을 넣고 배포합니다. 서버가 시작할 때 한 번만 모든 데이터를 지우고 시드를 다시 넣고, 적용한 값을 DB에 기록해 둡니다. 같은 값으로는 다시 지우지 않으니 변수는 그대로 두어도 됩니다. 가입한 사용자의 계정도 함께 지워지니 주의합니다.

## 4. Vercel 프론트엔드

1. Vercel에서 Add New, Project를 고르고 이 저장소를 가져옵니다.
2. Root Directory를 `frontend`로 정합니다. Next.js는 자동으로 인식됩니다.
3. Environment Variables에 `NEXT_PUBLIC_API_BASE_URL` = `https://<백엔드 주소>/api/v1`을 넣습니다.
4. 배포가 끝나면 나온 주소를 Railway 백엔드의 `CORS_ORIGINS`에 넣고 백엔드를 다시 배포합니다. 반영까지 1~2분 걸립니다.

## 5. 확인

Vercel 주소에서 가입하고 100토큰이 들어오는지, "AI가 내 재능 찾아 주기"가 동작하는지 봅니다. 브라우저 개발자 도구에 CORS 오류가 나오면 `CORS_ORIGINS` 값 끝에 `/`가 붙어 있지 않은지 확인합니다.

## 현재 운영 환경

- 프론트: https://inyeongori.vercel.app
- 백엔드: https://inyeongori-production.up.railway.app
- DB 서비스 이름이 `pgvector`라서 `DATABASE_URL=${{pgvector.DATABASE_URL}}`를 씁니다.
- 변수 원본은 로컬의 `.env.railway`(git 제외)에 있습니다. 운영 데모 비밀번호도 이 파일의 `SEED_PASSWORD`입니다.

## 비용과 제한

- Gemini 무료 등급은 분당 호출 수에 제한이 있습니다. 시연 중 연달아 누르면 무료 사용 한도 메시지가 나올 수 있으니 잠시 후 다시 시도합니다.
- Railway는 사용량만큼 과금합니다. 시연이 끝나면 서비스를 멈춰 두면 비용이 거의 들지 않습니다.
- 시연 직전에 AI가 불안하면 `AI_MOCK=true`로 바꿉니다. 임베딩도 예시 방식으로 바뀌므로 시드를 다시 넣어야 매칭 결과가 맞습니다.
