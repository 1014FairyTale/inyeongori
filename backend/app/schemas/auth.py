from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    nickname: str = Field(min_length=1, max_length=40)
    school: str | None = Field(default=None, max_length=80)
    major: str | None = Field(default=None, max_length=80)

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()

    @field_validator("nickname")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해 주세요")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class WalletBrief(BaseModel):
    available: int
    escrow: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nickname: str
    school: str | None
    major: str | None
    bio: str | None


class DueReviewOut(BaseModel):
    exchange_id: int
    listing_title: str | None
    provider_nickname: str
    due_at: datetime
    overdue: bool


class ReviewStatus(BaseModel):
    blocked: bool  # 기한을 넘긴 후기가 있어서 이용이 막혔는지
    due: list[DueReviewOut]  # 써야 하는 후기 (기한이 가까운 순)


class StepOut(BaseModel):
    key: str  # discover / list / request / chat / review
    done: bool


class GettingStarted(BaseModel):
    tutorial_seen: bool  # 가입 후 이용 가이드를 봤는지 (안 봤으면 가이드를 띄워요)
    steps: list[StepOut]  # 첫 걸음 체크리스트


class MeOut(BaseModel):
    user: UserOut
    wallet: WalletBrief
    review_status: ReviewStatus = ReviewStatus(blocked=False, due=[])
    getting_started: GettingStarted = GettingStarted(tutorial_seen=True, steps=[])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    me: MeOut
