from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.db.session import build_engine, build_session_factory


def test_settings_exposes_database_url() -> None:
    assert settings.database_url


def test_settings_exposes_reddit_configuration_fields() -> None:
    assert settings.reddit_client_id is not None
    assert settings.reddit_client_secret is not None
    assert settings.reddit_user_agent


def test_settings_exposes_producthunt_configuration_fields() -> None:
    assert settings.producthunt_client_id is not None
    assert settings.producthunt_client_secret is not None


def test_settings_exposes_youtube_configuration_field() -> None:
    assert settings.youtube_api_key is not None


def test_build_engine_returns_sqlalchemy_engine() -> None:
    engine = build_engine("sqlite+pysqlite:///:memory:")

    assert isinstance(engine, Engine)
    assert str(engine.url).startswith("sqlite+pysqlite://")


def test_build_session_factory_returns_working_session() -> None:
    engine = build_engine("sqlite+pysqlite:///:memory:")
    session_factory = build_session_factory(engine)

    with session_factory() as session:
        assert isinstance(session, Session)
