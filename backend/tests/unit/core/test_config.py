import pytest

from app.core.config import Settings, docs_urls


def test_jwt_secret_file_overrides_the_env_value(tmp_path) -> None:
    secret_file = tmp_path / "jwt_secret"
    secret_file.write_text("el-secreto-de-verdad\n", encoding="utf-8")

    settings = Settings(jwt_secret="change-me", jwt_secret_file=str(secret_file))

    assert settings.jwt_secret == "el-secreto-de-verdad"


def test_database_password_file_overrides_the_password_in_the_url(tmp_path) -> None:
    password_file = tmp_path / "db_password"
    password_file.write_text("p@ss w/rd\n", encoding="utf-8")

    settings = Settings(
        database_url="postgresql+asyncpg://dentia:placeholder@db:5432/dentia",
        database_password_file=str(password_file),
    )

    assert settings.database_url == ("postgresql+asyncpg://dentia:p%40ss%20w%2Frd@db:5432/dentia")


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


def test_app_version_defaults_to_dev() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_version == "dev"


def test_app_version_reads_from_version_env_var(monkeypatch) -> None:
    # Mismo nombre que ya escribe deploy/vps/scripts/deploy.sh en compose/.env
    # y que docker-compose.yml reenvia al contenedor de la API -- ver
    # Settings.app_version (CLAUDE.md sec. 6, "version_info").
    monkeypatch.setenv("VERSION", "1.4.0")
    settings = Settings(_env_file=None)
    assert settings.app_version == "1.4.0"
