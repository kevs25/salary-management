from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="ignore")

    # e.g. mysql+pymysql://user:password@host:port/dbname - no default, so a missing
    # setting fails loudly instead of quietly pointing somewhere else.
    database_url: str | None = None
    # CA certificate for TLS to a managed MySQL (e.g. Aiven). Kept out of the URL so the
    # same URL works on the host and in the container, where the file path differs.
    db_ssl_ca: str | None = None
    # Integration tests only: a separate database whose name ends in _test.
    test_database_url: str | None = None
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 3600  # below MySQL's default wait_timeout of 8h
    sql_echo: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
