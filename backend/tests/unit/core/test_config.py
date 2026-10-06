import pytest

from app.core.config import Settings, docs_urls


def test_production_rejects_default_jwt_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret="change-me")


def test_production_accepts_a_custom_jwt_secret() -> None:
    Settings(environment="production", jwt_secret="un-secreto-real-y-largo")


def test_development_allows_the_default_jwt_secret() -> None:
    Settings(environment="development", jwt_secret="change-me")


def test_docs_urls_disabled_in_production() -> None:
    assert docs_urls("production") == (None, None, None)


def test_docs_urls_enabled_outside_production() -> None:
    assert docs_urls("development") == ("/docs", "/redoc", "/openapi.json")
