from app.config import Settings


def test_database_url_scheme_is_normalized_for_psycopg() -> None:
    s = Settings(database_url="postgresql://u:p@host:5432/db", test_database_url="postgres://u:p@h/t")
    assert s.database_url == "postgresql+psycopg://u:p@host:5432/db"
    assert s.test_database_url == "postgresql+psycopg://u:p@h/t"
    assert Settings(database_url="postgresql+psycopg://x@y/z").database_url == "postgresql+psycopg://x@y/z"
