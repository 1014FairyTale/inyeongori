"""정책 수치는 전부 여기서 조정해요. (README "결정 사항"과 같이 갱신)"""

# ---- 토큰 ----
# 토큰은 '가격' 개념이에요. 제공자가 상품 가격을 정하고, 시간과는 관계없어요.
SIGNUP_BONUS_TOKENS = 100
BONUS_POOL_INITIAL_TOKENS = 100_000

# ---- 재능 마켓 ----
LISTING_MIN_PRICE = 1
LISTING_MAX_PRICE = 500
LISTING_CATEGORIES = [
    "학업·과제",
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

# ---- 매칭 (D3, 6단계에서 사용) ----
MATCH_TOP_N = 5
MATCH_WEIGHT_SIMILARITY = 0.7
MATCH_WEIGHT_RATING = 0.2
MATCH_WEIGHT_ACTIVITY = 0.1
MATCH_RATING_PRIOR = 3.5
MATCH_RATING_PRIOR_WEIGHT = 3

# ---- 부탁 쪼개기 적정 토큰 (5단계에서 사용) ----
# 비슷한 상품 가격의 중앙값을 쓰고, 비슷한 상품이 이 개수보다 적으면 AI 추정으로 넘어가요.
PRICE_SUGGEST_MIN_SIMILAR = 3
PRICE_SUGGEST_SIMILARITY_THRESHOLD = 0.55
