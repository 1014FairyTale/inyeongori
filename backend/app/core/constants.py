"""정책 수치는 전부 여기서 조정해요. (docs/decisions.md와 같이 갱신)"""

# ---- 토큰 ----
# 토큰은 '가격' 개념이에요. 제공자가 상품 가격을 정하고, 시간과는 관계없어요.
SIGNUP_BONUS_TOKENS = 100
BONUS_POOL_INITIAL_TOKENS = 100_000

# ---- 재능 마켓 ----
LISTING_MIN_PRICE = 1
LISTING_MAX_PRICE = 500
LISTING_CATEGORIES = [
    "공부·학습",
    "발표·PPT",
    "디자인",
    "개발·IT",
    "엑셀·문서",
    "어학",
    "음악·예술",
    "운동·게임",
    "진로·취업",
    "생활·기타",
]

# ---- 후기 보너스 (D5-A, 7단계에서 사용) ----
BONUS_MIN_CONTRIBUTION_SCORE = 70
BONUS_MIN_RATING = 4
BONUS_MIN_REVIEW_CHARS = 20
BONUS_TIERS = [  # (최소 점수, 거래가 대비 비율)
    (85, 0.20),
    (70, 0.10),
]
BONUS_MIN_TOKENS = 1
BONUS_MAX_TOKENS_PER_EXCHANGE = 10
BONUS_MAX_TOKENS_PER_PROVIDER_PER_DAY = 30
REPEAT_PAIR_WINDOW_DAYS = 30
REPEAT_PAIR_MULTIPLIERS = [1.0, 0.5, 0.0]  # 같은 두 사람의 1번째, 2번째, 3번째 이후 거래

# ---- 후기 작성자 보상·기한 (기획자 결정, 2026-11-15) ----
# 요청자가 완료 후 기한 안에 '성의 있는' 후기를 쓰면 거래가의 10%를 보너스 풀에서 돌려받아요.
# 성의 = AI 후기 성의 점수(구체성·거래 관련성·별점과 내용의 일치, 만족도와는 별개) + 최소 글자 수
REVIEW_REWARD_RATE = 0.10
REVIEW_REWARD_MIN_TOKENS = 1
REVIEW_REWARD_MIN_QUALITY = 70
REVIEW_REWARD_MIN_CHARS = 30
# 완료 후 이 기간 안에 후기를 안 쓰면 서비스 이용이 막혀요 (후기를 쓰면 풀림, 늦은 후기는 10% 없음)
REVIEW_DEADLINE_DAYS = 7

# ---- 매칭 (D3, 6단계에서 사용) ----
MATCH_TOP_N = 5
MATCH_WEIGHT_SIMILARITY = 0.7
MATCH_WEIGHT_RATING = 0.2
MATCH_WEIGHT_ACTIVITY = 0.1
MATCH_RATING_PRIOR = 3.5
MATCH_RATING_PRIOR_WEIGHT = 3
# ---- 임베딩 유사도 기준 (모델마다 점수 분포가 달라서 따로 둬요) ----
#  price    : 시세 계산에 '비슷한 재능'으로 셀 최소 유사도 (엄격)
#  match    : 매칭 후보로 보여 줄 최소 유사도
#  relative : 1등보다 이만큼 이상 낮으면 빼요 (관련 없는 사람·상품이 섞이지 않게)
#  strong   : 이 이상이면 1등과의 차이와 상관없이 남겨요 (1등이 아주 높을 때 관련 있는 2등이 잘리지 않게)
# 실측 (2026-11-14, 질문 7개 × 재능 7개):
#  - bge-m3              관련 min 0.49 / avg 0.63, 무관 max 0.47 / avg 0.38
#  - gemini-embedding-001 관련 min 0.85 / avg 0.89, 무관 max 0.83 / avg 0.75 (점수가 위쪽에 몰려 있음)
# 데모 리허설: 1등 0.83, 관련 있는 2등 0.63이 relative만으로는 잘려서 strong 추가
EMBEDDING_THRESHOLDS: dict[str, dict[str, float]] = {
    "BAAI/bge-m3": {"price": 0.55, "match": 0.48, "relative": 0.12, "strong": 0.58},
    "gemini-embedding-001": {"price": 0.86, "match": 0.84, "relative": 0.05, "strong": 0.87},
    "mock-ngram": {"price": 0.25, "match": 0.22, "relative": 0.12, "strong": 0.35},
}
EMBEDDING_THRESHOLDS_DEFAULT = EMBEDDING_THRESHOLDS["BAAI/bge-m3"]

# ---- 부탁 쪼개기 적정 토큰 (5단계에서 사용) ----
# 비슷한 상품 가격의 중앙값을 쓰고, 비슷한 상품이 이 개수보다 적으면 AI 추정으로 넘어가요.
PRICE_SUGGEST_MIN_SIMILAR = 3
PRICE_SUGGEST_TOP_K = 5
PRICE_FALLBACK_TOKENS = 30  # 시세도 AI 추정도 없을 때 (예: 사용자가 직접 추가한 활동)

# ---- 부탁 쪼개기 ----
PLAN_MAX_ITEMS = 12
