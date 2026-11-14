from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 설정. 비밀값은 반드시 .env(또는 배포 환경변수)로만 넣어요."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://inyeongori:change-me@localhost:5432/inyeongori"
    test_database_url: str = "postgresql+psycopg://inyeongori:change-me@localhost:5432/inyeongori_test"

    jwt_secret: str = "dev-only-insecure-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:3000"

    ai_mock: bool = True
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    llm_model: str = "gemini-3.5-flash-lite"
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _psycopg_scheme(cls, v: str) -> str:
        """Railway 등은 postgresql:// 또는 postgres:// 로 줘요. SQLAlchemy가 psycopg3를 쓰도록 바꿔요."""
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
