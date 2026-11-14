"""테스트는 실제 PostgreSQL(TEST_DATABASE_URL)에서 돌아요.

SQLite로는 SELECT ... FOR UPDATE 동시성 테스트를 할 수 없어서예요.
먼저 `docker compose up -d db` 로 DB를 띄워 주세요.
"""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("AI_MOCK", "true")

from app.config import get_settings  # noqa: E402
from app.core.constants import BONUS_POOL_INITIAL_TOKENS  # noqa: E402
from app.db import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.ledger import ensure_system_accounts  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_URL = get_settings().test_database_url

engine = create_engine(TEST_URL, pool_pre_ping=True, pool_size=20, max_overflow=10)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _migrate() -> Iterator[None]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        pytest.exit(
            f"테스트 DB에 연결할 수 없어요 ({TEST_URL}). `docker compose up -d db` 후 다시 실행해 주세요.\n{e}",
            returncode=2,
        )
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_db() -> Iterator[None]:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE ledger_transfers, token_accounts, users RESTART IDENTITY CASCADE"))
    with TestingSession() as db:
        ensure_system_accounts(db, BONUS_POOL_INITIAL_TOKENS)
        db.commit()
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    with TestingSession() as s:
        yield s


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(run_bootstrap=False)

    def _get_db() -> Iterator[Session]:
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c


def signup(client: TestClient, email: str = "a@example.com", nickname: str = "새내기") -> dict:
    r = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "password123", "nickname": nickname},
    )
    assert r.status_code == 201, r.text
    return r.json()
