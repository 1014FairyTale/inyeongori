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


class MeOut(BaseModel):
    user: UserOut
    wallet: WalletBrief


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    me: MeOut
